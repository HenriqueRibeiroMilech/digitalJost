import atexit
import json
from functools import lru_cache

import pandas as pd

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from app.utils.db_utils import get_engine
from app.utils.teams_utils import send_teams_message
from backend.config import BackendConfig
from backend.modules.monitoring.current_status import CurrentStatusError, STATUS_COLUMNS, read_current_status


@lru_cache(maxsize=1)
def _sessions():
    config = BackendConfig.from_env()
    engine = create_engine(
        config.td_database_uri, pool_size=1, max_overflow=0,
        pool_timeout=config.td_pool_timeout, pool_recycle=config.td_pool_recycle,
        pool_pre_ping=True, hide_parameters=True,
    )
    atexit.register(engine.dispose)
    return sessionmaker(engine)


def default(logger):
    try:
        sessions = _sessions()
        stopped_machines = pd.DataFrame(read_current_status(
            sessions, mach2_engine=get_engine('plex'), ftm_engine=get_engine('ftm'), stops_only=True,
        ), columns=STATUS_COLUMNS)
        with sessions() as session:
            rows = session.execute(text(
                'SELECT userId, downtimeId, area, workcenter FROM JDT_DOWNTIME_ALERTS'
            )).mappings()
            userData = pd.DataFrame(rows, columns=['userId', 'downtimeId', 'area', 'workcenter'])
    except CurrentStatusError:
        raise
    except Exception:
        raise CurrentStatusError('Não foi possível carregar as fontes dos alertas de parada.') from None

    missing_code = stopped_machines['Event_Code'].eq('')
    if missing_code.any():
        logger.info('%s parada(s) sem código de motivo; não serão enviados alertas para elas.', int(missing_code.sum()))
    stopped_machines = stopped_machines[~missing_code]
    if stopped_machines.empty or userData.empty:
        return
    userData['downtimeId'] = userData['downtimeId'].fillna('').astype(str).str.replace(r'^(\d+)\.0$', r'\1', regex=True)

    userData['area'] = userData['area'].apply(json.loads)
    userData['workcenter'] = userData['workcenter'].apply(json.loads)

    events_by_group = pd.merge(left=stopped_machines, right=userData.explode(['area']), left_on=['Event_Code'], right_on=['downtimeId'], how='inner').dropna()
    events_by_group = events_by_group[events_by_group['Workcenter_Group'] == events_by_group['area']]
    events_by_workcenter = pd.merge(left=stopped_machines, right=userData.explode(['workcenter']), left_on=['Workcenter_Code'], right_on=['workcenter'], how='inner')
    events_by_workcenter = events_by_workcenter[events_by_workcenter['downtimeId'] == events_by_workcenter['Event_Code']]

    def send_data(row):

        title = 'NOTIFICAÇÃO DE PARADA'
        # Monta o Adaptive Card
        message_data = {
            "body": {
                "contentType": "html",
                "content": f'<p><span style="font-size: 20px;">🚨</span><b><strong class="editor-text-bold" style="font-size: 20px;"> </strong></b><b><strong class="editor-text-bold" style="font-size: 20px;">{title}</strong></b></p><attachment id="card"></attachment>'
            },
            "attachments": [
                {
                    "id": "card",
                    "contentType": "application/vnd.microsoft.card.adaptive",
                    "content": json.dumps({
                        "type": "AdaptiveCard",
                        "version": "1.5",
                        "$schema": "http://adaptivecards.io/schemas/adaptive-card.json",
                        "body": [
                            {
                                "type": "ColumnSet",
                                "columns": [
                                    {
                                        "type": "Column",
                                        "width": "auto",
                                        "items": [
                                            {
                                                "type": "TextBlock",
                                                "text": "🏭 Centro de Trabalho:",
                                                "wrap": True,
                                                "weight": "Bolder"
                                            }
                                        ],
                                        "horizontalAlignment": "Left"
                                    },
                                    {
                                        "type": "Column",
                                        "width": "stretch",
                                        "horizontalAlignment": "Right",
                                        "items": [
                                            {
                                                "type": "TextBlock",
                                                "wrap": True,
                                                "id": "Workcenter",
                                                "text": str(row['Workcenter'])
                                            }
                                        ]
                                    }
                                ]
                            },
                            {
                                "type": "ColumnSet",
                                "columns": [
                                    {
                                        "type": "Column",
                                        "width": "auto",
                                        "items": [
                                            {
                                                "type": "TextBlock",
                                                "text": "🔎 Motivo:",
                                                "wrap": True,
                                                "weight": "Bolder"
                                            }
                                        ],
                                        "horizontalAlignment": "Left"
                                    },
                                    {
                                        "type": "Column",
                                        "width": "stretch",
                                        "horizontalAlignment": "Right",
                                        "items": [
                                            {
                                                "type": "TextBlock",
                                                "wrap": True,
                                                "id": "Motive",
                                                "text": str(row['Event'])
                                            }
                                        ]
                                    }
                                ]
                            },
                            {
                                "type": "ColumnSet",
                                "columns": [
                                    {
                                        "type": "Column",
                                        "width": "auto",
                                        "items": [
                                            {
                                                "type": "TextBlock",
                                                "text": "⏱️ Horário de Início:",
                                                "wrap": True,
                                                "weight": "Bolder"
                                            }
                                        ],
                                        "horizontalAlignment": "Left"
                                    },
                                    {
                                        "type": "Column",
                                        "width": "stretch",
                                        "horizontalAlignment": "Right",
                                        "items": [
                                            {
                                                "type": "TextBlock",
                                                "wrap": True,
                                                "id": "Datetime",
                                                "text": row['Log_Date']
                                            }
                                        ]
                                    }
                                ]
                            },
                            {
                                "type": "ColumnSet",
                                "columns": [
                                    {
                                        "type": "Column",
                                        "width": "auto",
                                        "items": [
                                            {
                                                "type": "TextBlock",
                                                "text": "⏳ Duração:",
                                                "wrap": True,
                                                "weight": "Bolder"
                                            }
                                        ],
                                        "horizontalAlignment": "Left"
                                    },
                                    {
                                        "type": "Column",
                                        "width": "stretch",
                                        "horizontalAlignment": "Right",
                                        "items": [
                                            {
                                                "type": "TextBlock",
                                                "wrap": True,
                                                "id": "Duration",
                                                "text": str(row['Log_Duration'])
                                            }
                                        ]
                                    }
                                ]
                            }
                        ]
                    })
                }
            ]
        }

        send_teams_message(
            user_id=row['userId']
            , message=message_data
        )

    if not events_by_group.empty:
        events_by_group.apply(send_data, axis=1)
    if not events_by_workcenter.empty:
        events_by_workcenter.apply(send_data, axis=1)
