import json
import pandas as pd
import urllib

from sqlalchemy import create_engine

from app.utils.constants import CNNX_JDT
from app.utils.teams_utils import send_teams_message

def default(logger):

    engine_jdt = create_engine( f"mssql+pyodbc:///?odbc_connect={urllib.parse.quote_plus(CNNX_JDT)}",)

    with engine_jdt.connect() as conn:
        query = f"""SELECT 
                        Workcenter_Code
                        , CONCAT(Workcenter_Code, '-' + Name) AS Workcenter
                        , Workcenter_Group
                        , FORMAT(Log_Date, 'dd/MM/yyyy HH:mm:ss') AS Log_Date
                        , Log_Duration
                        , Event
                        , LEFT(Event, CHARINDEX('-', Event) - 1) AS Event_Code
                FROM TEMP_WORKCENTER_STATUS
                ORDER BY Workcenter_Group, Log_Date ASC"""
        stopped_machines = pd.read_sql(query, conn)

        query = f"""SELECT userId, downtimeId, area, workcenter FROM JDT_DOWNTIME_ALERTS"""
        userData = pd.read_sql(query, conn)


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

    events_by_group.apply(send_data, axis=1)
    events_by_workcenter.apply(send_data, axis=1)