from datetime import datetime, timedelta
from requests.auth import HTTPBasicAuth

import pandas as pd

from flask_mail import Message
from flask import Blueprint, abort, redirect, render_template, request, url_for
from flask_login import current_user
from sqlalchemy import text

from app.utils.business import getStopsData
from app.utils.constants import MES_MAIN_PASSWORD, MES_MAIN_USER
from app.utils.data_utils import POST_WITH_AUTH
from app.utils.db_utils import engine_run_query, get_engine
from app.config import mail
from app.utils.dynamic_constants import getPlex
from app.utils.permissions import get_permission
from sqlalchemy.exc import IntegrityError

_PROBLEM_CATEGORY = pd.DataFrame([
                                {"areaId": 8, "Code": 2}
                                , {"areaId": 12, "Code": 3}
                                , {"areaId": 12, "Code": 4}
                                , {"areaId": 8, "Code": 5}
                                , {"areaId": 8, "Code": 6}
                                , {"areaId": 8,   "Code": 7}
                                , {"areaId": 13,  "Code": 8}
                                , {"areaId": 13,  "Code": 9}
                                , {"areaId": 13,  "Code": 10}
                                , {"areaId": 13,  "Code": 11}
                                , {"areaId": 8,   "Code": 12}
                                , {"areaId": 2,   "Code": 13}
                                , {"areaId": 8,   "Code": 14}
                                , {"areaId": 8,   "Code": 15}
                                , {"areaId": 13,  "Code": 16}
                                , {"areaId": 13,  "Code": 18}
                                , {"areaId": 12,  "Code": 19}
                                , {"areaId": 2,   "Code": 20}
                                , {"areaId": 13,  "Code": 22}
                                , {"areaId": 2,   "Code": 31}
                                , {"areaId": 2,   "Code": 32}
                                , {"areaId": 13,  "Code": 35}
                                , {"areaId": 2,   "Code": 37}
                                , {"areaId": 12,  "Code": 42}
                                , {"areaId": 2,   "Code": 43}
                                , {"areaId": 2,   "Code": 44}
                                , {"areaId": 13,  "Code": 45}
                                , {"areaId": 13,  "Code": 46}
                                , {"areaId": 3,   "Code": 50}
                                , {"areaId": 3,   "Code": 51}
                                , {"areaId": 3,   "Code": 52}
                                , {"areaId": 3,   "Code": 53}
                                , {"areaId": 3,   "Code": 54}
                                , {"areaId": 8,   "Code": 55}
                                , {"areaId": 13,  "Code": 56}
                                , {"areaId": 13,  "Code": 58}
                                , {"areaId": 8,   "Code": 59}
                                , {"areaId": 8,   "Code": 60}
                                , {"areaId": 13,  "Code": 61}
                                , {"areaId": 3,   "Code": 62}
                                , {"areaId": 12,  "Code": 65}
                                , {"areaId": 13,  "Code": 66}
                                , {"areaId": 2,   "Code": 100}
                            ])

_USER_FILTERS = {}

request_workcentersLogChange_bp = Blueprint('request_workcentersLogChange', __name__)

@request_workcentersLogChange_bp.before_request
def route_auth():
    # Verifica se o usuário está autenticado
    if not current_user.is_authenticated:
        return redirect(url_for('auth.login', next=request.url))

    # Verifica permissão geral
    if not get_permission('GENERAL').can():
        return abort(403)


# PÁGINA DE ROTAS
@request_workcentersLogChange_bp.route('/oee/paradas/alterar', methods=['GET'])
def stopChanges_home():

    query = f"""
    SELECT 
        SUM(CASE WHEN (approver1 = '{current_user.id}' AND approverStatus1 = 0) OR (approver2 = '{current_user.id}' AND approverStatus2 = 0) THEN 1 ELSE 0 END) AS s0,
        SUM(CASE WHEN (approver1 = '{current_user.id}' AND approverStatus1 = 1) OR (approver2 = '{current_user.id}' AND approverStatus2 = 1) THEN 1 ELSE 0 END) AS s1,
        SUM(CASE WHEN (approver1 = '{current_user.id}' AND approverStatus1 = 2) OR (approver2 = '{current_user.id}' AND approverStatus2 = 2) THEN 1 ELSE 0 END) AS s2,
        SUM(CASE WHEN requesterId = '{current_user.id}' THEN 1 ELSE 0 END) AS r0

    FROM JDT_REQUEST_STOPCHANGES;
    """

    results = engine_run_query(query, 'jdt')

    status0 = results['s0'][0]
    status1 = results['s1'][0]
    status2 = results['s2'][0]
    requests = results['r0'][0]

    return render_template('request.stopChanges/stopChanges_main.html', status0=status0, status1=status1, status2=status2, requests=requests)


# MÉTODO PARA CONSULTAR AS PARADAS E SOLICITAR UMA ALTERAÇÃO DE PARADA
@request_workcentersLogChange_bp.route('/oee/paradas/alterar/solicitar', methods=['GET', 'POST'])
def stopChanges_main():
    
    if request.method == 'POST':

        if request.args['type'] == 'search':

            payload = request.get_json()
            _USER_FILTERS[current_user.id] = payload

            payload['start_date'] = payload['start_date'].replace('T', ' ') + ':00'
            payload['end_date'] = payload['end_date'].replace('T', ' ') + ':00'

            data = getStopsData(payload)

            query = f"""SELECT 

                            T1.eventId
                            , T2.name as approver1
                            , T3.name as approver2
                            , T1.approverStatus1
                            , T1.approverStatus2
                            , T1.motive2
                            , 1 AS requested
            
                        FROM JDT_REQUEST_STOPCHANGES T1

                        LEFT JOIN JDT_USER_DETAILS AS T2 ON T1.approver1 = T2.id
                        LEFT JOIN JDT_USER_DETAILS AS T3 ON T1.approver2 = T3.id

                        WHERE T1.approverStatus1 = 0 OR T1.approverStatus2 = 0"""
            table = engine_run_query(query, 'jdt')

            data = pd.merge(left=data, right=table, left_on='Log_Key', right_on='eventId', how='left')

            return data.to_json(orient='records')
        
        else:
            
            payload = request.get_json()

            if payload.get('Plex'):
                
                query = f"""

                            SELECT 

                                Workcenter_Key
                                , CONCAT(Workcenter_Code, '-', Workcenter_Name) AS Workcenter_Name
                                , FORMAT(Log_Date, 'dd/MM/yyyy HH:mm:ss') AS Log_Date
                                , FORMAT(DATEADD(MINUTE, Log_Hours * 60.0, Log_Date), 'dd/MM/yyyy HH:mm:ss') AS End_Date
                                , CAST(ROUND(Log_Hours * 60, 0) AS INT) AS Log_Minutes
                                , Code
                                , CASE Shift
                                    WHEN 'Primeiro' THEN 1
                                    WHEN 'Segundo' THEN 2
                                    WHEN 'Terceiro' THEN 3
                                END AS Shift

                            FROM OPENQUERY([PLEX_DSN_JOST], '

                                SELECT

                                    T1.Workcenter_Key
                                    , T1.Log_Date
                                    , T1.Log_Hours
                                    , T2.Name AS Workcenter_Name
                                    , T2.Workcenter_Code
                                    , T3.Code AS Code
                                    , T5.Shift_Group AS Shift
                                    , T1.Log_Key

                                FROM

                                    Part_v_Workcenter_Log T1
                                    JOIN Part_v_Workcenter T2 ON T1.Workcenter_Key = T2.Workcenter_Key
                                    LEFT JOIN Part_v_Workcenter_Event T3 ON T1.Workcenter_Event_Key = T3.Workcenter_Event_Key
                                    JOIN Common_v_Shift T5 ON T1.Shift_Key = T5.Shift_Key

                                WHERE
                                    T1.Log_Key = {payload['Log_Key']}
                                ') EH
                            
                            WHERE NOT EXISTS (
                                SELECT 1 
                                FROM JDT_REQUEST_STOPCHANGES JDT 
                                WHERE JDT.eventId = EH.Log_Key
                                    AND (JDT.finalDate IS NULL OR JDT.finalDate < DATEADD(HOUR, -4, GETDATE()))
                            );
                """ 

            else:  

                query = f"""

                            SELECT 
                                TRIM(sDescription) AS Workcenter_Name
                                , FORMAT(tStart, 'dd/MM/yyyy HH:mm:ss') AS Log_Date
                                , FORMAT(tEnd, 'dd/MM/yyyy HH:mm:ss') AS End_Date
                                , DATEDIFF(MINUTE, tStart, tEnd) AS Log_Minutes
                                , CAST(SUBSTRING(TRIM(sEndVal), 0, 4) AS INT) AS Code
                                , CASE sShift
                                    WHEN 'TURNO 1' THEN 1
                                    WHEN 'TURNO 2' THEN 2
                                    WHEN 'TURNO 3' THEN 3
                                END AS Shift

                            FROM FTMETRICS_JOST.dbo.OEEQEventHistory EH
                            WHERE lOEEEventId = {payload['Log_Key']}
                            AND NOT EXISTS (
                                SELECT 1 
                                FROM JDT_REQUEST_STOPCHANGES JDT 
                                WHERE JDT.eventId = EH.lOEEEventId
                                    AND (JDT.finalDate IS NULL OR JDT.finalDate < DATEADD(HOUR, -4, GETDATE()))
                            );
                """
            
            engine = get_engine('jdt')
            with engine.connect() as cnnx:
                check_request = pd.read_sql(query, cnnx)

                if check_request.empty:
                    return 'A REQUEST ALREADY EXISTS WITHIN THIS EVENT.', 403                        
                
                check_request = check_request.iloc[0]

                query = f"""SELECT 
                            T1.userId
                            , T1.areaId
                            , T1.shift
                            , T2.companyEmail
                        FROM 
                            JDT_USER_STOPCHANGES AS T1
                            LEFT JOIN JDT_USER_DETAILS AS T2 ON T2.id = T1.userId"""   
                approvers_info = pd.read_sql(query, cnnx)

                problemAreaOld = _PROBLEM_CATEGORY[_PROBLEM_CATEGORY['Code'] == int(check_request['Code'])]['areaId'].iloc[0]
                problemAreaNew = _PROBLEM_CATEGORY[_PROBLEM_CATEGORY['Code'] == int(payload["newMotive"])]['areaId'].iloc[0]

                approver1 = approvers_info[(approvers_info['areaId'] == problemAreaOld)]
                if len(approver1) > 1:
                    approver1 = approver1[(approvers_info['shift'] == check_request['Shift'])]

                approver2 = approvers_info[(approvers_info['areaId'] == problemAreaNew)]
                if len(approver2) > 1:
                    approver2 = approver2[(approvers_info['shift'] == check_request['Shift'])]


                query = f"""SELECT COALESCE(MAX(requestId) + 1, 1) AS newId FROM JDT_REQUEST_STOPCHANGES"""
                newId = pd.read_sql(query, cnnx)['newId'][0]

                query = f"""
                            INSERT INTO JDT_REQUEST_STOPCHANGES VALUES (
                                '{newId}'
                                , '{current_user.id}'
                                , '{approver1['userId'].iloc[0]}'
                                , '{approver2['userId'].iloc[0]}'
                                , GETDATE(), NULL, 0, 0, NULL, NULL
                                , '{check_request['Code']}'
                                , '{payload["newMotive"]}'
                                , {payload['Plex']}
                                , {payload['Log_Key']}
                                , '{payload["requestText"]}'
                                , NULL)
                """
                cnnx.execute(text(query))
            
                if payload['Plex']:

                    try:
                        query = f"""
                                INSERT INTO JDT_REQUEST_STOPCHANGES_PLEX (
                                    eventId
                                    , workcenter
                                    , startDate
                                    , endDate
                                    , logMinutes
                                ) VALUES (
                                    {payload['Log_Key']}
                                    , {check_request['Workcenter_Key']}
                                    , '{pd.to_datetime(check_request['Log_Date'], format='%d/%m/%Y %H:%M:%S')}'
                                    , '{pd.to_datetime(check_request['End_Date'], format='%d/%m/%Y %H:%M:%S')}'
                                    , {check_request['Log_Minutes']}
                                )
                        """
                        cnnx.execute(text(query))
                    except Exception as e:
                        # SQLAlchemy IntegrityError is sqlalchemy.exc.IntegrityError
                        print(e, flush=True)
                        if isinstance(e, IntegrityError):
                            # SQL Server error codes for duplicate key: 2627, 2601
                            if any(code in str(e.orig) for code in ['2627', '2601']):
                                pass
                            else:
                                return 'INTERN SERVER ERROR.', 500
                        else:
                            return 'INTERN SERVER ERROR.', 500

                cnnx.commit()

            msg = Message(f'Alteração de Paradas - Nova Solicitação',
                sender=('Transformação Digital JOST', 'noreply.digitaljost@randon.com.br'),
                recipients=[approver1['companyEmail'].iloc[0], approver2['companyEmail'].iloc[0]])
            
            def format_code_description(code):
                row = getPlex('events')[getPlex('events')['Code'] == str(code)].iloc[0]
                return f"{row['Code']}-{row['Description']}"
            
            msg.html = render_template('request.stopChanges/stopChanges_email_new_request.html'
                                        , requestId=newId
                                        , userName=current_user.name
                                        , workCenter=check_request['Workcenter_Name']
                                        , stopDate=check_request['Log_Date']
                                        , shift=check_request['Shift']
                                        , duration=check_request['Log_Minutes']
                                        , motiveOld=format_code_description(check_request["Code"])
                                        , motiveNew=format_code_description(payload["newMotive"])
                                        , requestText=payload["requestText"])
            
            mail.send(msg)

            return f'NEW ID {str(newId)}'                        
    
    else:

        query = f"""SELECT 
                        GRUPO AS Workcenter_Group
                        , LEFT(NOME_MAQUINA, CHARINDEX('-', NOME_MAQUINA) - 1) AS Workcenter_Code
                        , SUBSTRING(NOME_MAQUINA, CHARINDEX('-', NOME_MAQUINA) + 1, LEN(NOME_MAQUINA)) AS Name
                        , 1 AS Workcenter_Key
                    FROM CONFIG_TABLET WHERE CT_PLEX IS NULL"""
        mic_workcenters = engine_run_query(query, 'ftm')
        mes_workcenters = getPlex('workcenters')[['Workcenter_Group', 'Workcenter_Code', 'Name', 'Workcenter_Key']]
        workcenters = pd.concat([mes_workcenters[~mes_workcenters['Workcenter_Code'].isin(mic_workcenters['Workcenter_Code'])], mic_workcenters])
        
        data = pd.DataFrame(columns=["sDescription", "tStart", "tEnd", "sEndVal", "dDuration"])
        if current_user.id not in _USER_FILTERS.keys():
            _USER_FILTERS[current_user.id] = {
                'shift' : ['1', '2', '3', 'Extra']
                , 'm_event': []
                , 'w_name_mic': []
                , 'start_date': ''
                , 'end_date': ''
                , 'w_name_plex': []
            }

        current_user_filters = _USER_FILTERS[current_user.id]

        events = getPlex('events')
        events = events[(events['Code'] != '64') & (events['Active'] == 1) & (events['Workcenter_Event_Group'] != 'Programada')]
        events = events.sort_values(by='Code', key=lambda col: col.fillna('0').astype(int)).to_dict(orient='records')

        return render_template('request.stopChanges/stopChanges_request.html'
                                , workcenters=workcenters.sort_values(by="Workcenter_Code").to_dict(orient='records')
                                , events=events
                                , data=data.to_json(orient='records')
                                , workCenterFilter=current_user_filters['w_name_plex'] or current_user_filters['w_name_mic']
                                , motiveFilter=current_user_filters['m_event']
                                , initDateFilter=current_user_filters['start_date']
                                , endDateFilter=current_user_filters['end_date'])


# PÁGINA ONDE SE VISUALIZAM AS SOLICITAÇÕES FEITAS PELO USUÁRIO
@request_workcentersLogChange_bp.route('/oee/paradas/alterar/solicitacoes', methods=['GET', 'POST'])
def stopChanges_view():

    if request.method == 'GET':

        this_week = datetime.now().date()
        last_week = this_week - timedelta(weeks=2)

        return render_template('request.stopChanges/stopChanges_view.html', this_week=this_week, last_week=last_week)
    
    else:


        query = f"""
                    
            SELECT 
                T1.requestId
                , FORMAT(T1.openDate, 'dd/MM/yyyy') AS openDate
                , T1.motive1
                , T1.motive2
                , T1.approverStatus1
                , T1.approverStatus2
                , T1.Plex
                , COALESCE(CAST(T2.workcenter AS varchar), T3.sDescription) AS Workcenter_Name
                , FORMAT(COALESCE(T2.endDate, T3.tStart), 'dd/MM/yyyy') AS tStart
                , COALESCE(T2.logMinutes, T3.lSeconds / 60) AS dDuration
                , T4.name
            FROM 
                JDT_REQUEST_STOPCHANGES AS T1

                LEFT JOIN JDT_REQUEST_STOPCHANGES_PLEX AS T2 
                    ON T1.PLEX = 1 AND T1.eventId = T2.eventId

                LEFT JOIN FTMETRICS_JOST.dbo.OEEQEventHistory AS T3 
                    ON T1.PLEX = 0 AND T1.eventId = T3.lOEEEventId

                JOIN JDT_USER_DETAILS AS T4 ON T1.requesterId = T4.id
            
            WHERE 
                
                T1.openDate BETWEEN '{request.get_json()['last_week']} 00:00' AND '{request.get_json()['this_week']} 23:59'

            ORDER BY T1.openDate DESC"""

        table = engine_run_query(query, 'jdt')

        table = pd.merge(left=table, right=getPlex('events')[['Code', 'Description']], left_on="motive1", right_on="Code").rename(columns={'Description' : 'motiveDesc1'})
        table = pd.merge(left=table, right=getPlex('events')[['Code', 'Description']], left_on="motive2", right_on="Code").rename(columns={'Description' : 'motiveDesc2'})
        
        workcenters = getPlex('workcenters')
        workcenters['Workcenter_Key'] = workcenters['Workcenter_Key'].astype(str)

        map_dict = workcenters.set_index('Workcenter_Key').apply(
            lambda row: f"{row['Workcenter_Code']} - {row['Name']}", axis=1
        ).to_dict()
        
        table.loc[table['Plex'] == 1, 'Workcenter_Name'] = (
            table.loc[table['Plex'] == 1, 'Workcenter_Name'].map(map_dict)
        )

        return table.to_json(orient='records')


# ROTA PARA CONSULTAR UMA SOLICITAÇÃO DE PARADA EM ESPECIFICA E VER O SEU STATUS
@request_workcentersLogChange_bp.route('/oee/paradas/alterar/solicitacoes/<int:requestId>', methods=['GET'])
def stopChanges_status(requestId):

    query = f"""
                SELECT 
                    FORMAT(T1.openDate, 'dd/MM/yyyy HH:mm:ss') as openDate
                    , FORMAT(T1.finalDate, 'dd/MM/yyyy HH:mm:ss') as finalDate
                    , T1.motive1
                    , T1.motive2
                    , T1.approverStatus1
                    , T1.approverStatus2
                    , T1.eventId
                    , T1.requestId
                    , T1.deniedText
                    , T1.requestText
                    , T1.plex
                    , T2.name as requesterName
                    , T3.name as approver1
                    , GA1.name as approverArea1
                    , T4.name as approver2
                    , GA2.name as approverArea2
                FROM JDT_REQUEST_STOPCHANGES AS T1
                    JOIN JDT_USER_DETAILS AS T2 ON T1.requesterId = T2.id
                    LEFT JOIN JDT_USER_DETAILS AS T3 ON T1.approver1 = T3.id
                    LEFT JOIN JDT_USER_DETAILS AS T4 ON T1.approver2 = T4.id
                    LEFT JOIN JDT_GENERAL_AREA AS GA1 ON T3.areaId = GA1.areaId
                    LEFT JOIN JDT_GENERAL_AREA AS GA2 ON T4.areaId = GA2.areaId

                WHERE T1.requestId = {requestId}"""
    data = engine_run_query(query, 'jdt')

    if data.empty:
        return render_template('request.stopChanges/stopChanges_alert_not_exists.html'), 404

    data['eventId'] = data['eventId'].astype(int).astype(str)

    if data['plex'][0]:
        query = f"""
                    SELECT 
                        FORMAT(startDate, 'dd/MM/yyyy HH:mm:ss') AS startDate
                        , workcenter
                        , logMinutes
                    FROM JDT_REQUEST_STOPCHANGES_PLEX WHERE eventId = {data['eventId'][0]}
                """
    
    else:
        query = f"""
                    SELECT 
                        FORMAT(tStart, 'dd/MM/yyyy HH:mm:ss') AS startDate
                        , REPLACE(sDescription, '-', ' - ') AS workcenter
                        , lSeconds / 60 AS logMinutes
                    FROM [FTMETRICS_JOST].[dbo].[OEEQEventHistory] WHERE lOEEEventId = {data['eventId'][0]}
                """

    stop_data = engine_run_query(query, 'jdt')

    if data['plex'][0]:
        stop_data = pd.merge(left=stop_data, right=getPlex('workcenters')[['Workcenter_Key', 'Name', 'Workcenter_Code']], left_on='workcenter', right_on='Workcenter_Key')
        stop_data['workcenter'] = stop_data['Workcenter_Code'] + ' - ' + stop_data['Name']
    
    data = pd.merge(left=data, right=getPlex('events')[['Code', 'Description']], left_on="motive1", right_on="Code").rename(columns={'Description' : 'motiveDesc1'})
    data = pd.merge(left=data, right=getPlex('events')[['Code', 'Description']], left_on="motive2", right_on="Code").rename(columns={'Description' : 'motiveDesc2'})

    back = request.args.get('origin', 'solicitacoes')

    return render_template(
        'request.stopChanges/stopChanges_status.html'
        , data=data.to_dict(orient="records")
        , stop_data=stop_data.to_dict(orient="records")
        , back=back, requestId=requestId
    )


# METODO PARA CONSULTA E APROVAÇÃO DAS SOLICITAÇÕES PENDENTES DE CADA USUÁRIO
# ADMIN CONSEGUE VER E APROVAR TODAS AS SOLICITAÇÕES PENDENTES
@request_workcentersLogChange_bp.route('/oee/paradas/alterar/pendencias', methods=['GET', 'POST'])
def stopChanges_manage():

    if request.method == 'GET':

        aux = 'T1.finalDate IS NULL'
        if not current_user.admin:       
            aux = f"""(T1.approver1 = '{current_user.id}' AND T1.approverStatus1 = 0) OR (T1.approver2 = '{current_user.id}' AND T1.approverStatus2 = 0)"""
        
        query = f"""
                    
                    SELECT 
                        T1.requestId
                        , FORMAT(T1.openDate, 'dd/MM/yyyy') AS openDate
                        , T1.motive1
                        , T1.motive2
                        , T1.approverStatus1
                        , T1.approverStatus2
                        , T1.Plex
                        , T1.requestText
                        , COALESCE(CAST(T2.workcenter AS varchar), T3.sDescription) AS Workcenter_Name
                        , FORMAT(COALESCE(T2.endDate, T3.tStart), 'dd/MM/yyyy') AS tStart
                        , COALESCE(T2.logMinutes, T3.lSeconds / 60) AS dDuration
                        , T4.name
                    FROM 
                        JDT_REQUEST_STOPCHANGES AS T1

                        LEFT JOIN JDT_REQUEST_STOPCHANGES_PLEX AS T2 
                            ON T1.PLEX = 1 AND T1.eventId = T2.eventId

                        LEFT JOIN FTMETRICS_JOST.dbo.OEEQEventHistory AS T3 
                            ON T1.PLEX = 0 AND T1.eventId = T3.lOEEEventId

                        JOIN JDT_USER_DETAILS AS T4 ON T1.requesterId = T4.id
                    
                    WHERE {aux}

                    ORDER BY T1.openDate ASC"""

        table = engine_run_query(query, 'jdt') 

        table = pd.merge(left=table, right=getPlex('events')[['Code', 'Description']], left_on="motive1", right_on="Code").rename(columns={'Description' : 'motiveDesc1'})
        table = pd.merge(left=table, right=getPlex('events')[['Code', 'Description']], left_on="motive2", right_on="Code").rename(columns={'Description' : 'motiveDesc2'})
        
        workcenters = getPlex('workcenters')
        workcenters['Workcenter_Key'] = workcenters['Workcenter_Key'].astype(str)

        map_dict = workcenters.set_index('Workcenter_Key').apply(
            lambda row: f"{row['Workcenter_Code']} - {row['Name']}", axis=1
        ).to_dict()

        table.loc[table['Plex'] == 1, 'Workcenter_Name'] = (
            table.loc[table['Plex'] == 1, 'Workcenter_Name'].map(map_dict)
        )

        return render_template('request.stopChanges/stopChanges_pending.html', table=table.to_json(orient='records'))
    
    else:

        received_data = request.get_json()

        query = f"""SELECT  
                        approver1, approverStatus1,
                        approver2, approverStatus2,
                        requestText, deniedText, finalDate, requesterId
                    
                    FROM JDT_REQUEST_STOPCHANGES WHERE requestId = {received_data['requestId']} ORDER BY openDate DESC"""
        check_request = engine_run_query(query, 'jdt')

        # SEÇÃO PARA VERIFICAR PERMISSÃO
        if len(check_request) == 0:
            abort(403)

        elif str(current_user.id) not in [str(check_request['approver1'][0]), str(check_request['approver2'][0])] and not current_user.admin:
            abort(403)
        
        elif check_request['finalDate'][0] == 'None':
            return render_template('request.stopChanges/stopChanges_alert_end.html'), 403
        
        elif str(check_request['approver1'][0]) == str(current_user.id) and check_request['approverStatus1'][0] != 0:
            abort(403)

        elif str(check_request['approver2'][0]) == str(current_user.id) and check_request['approverStatus2'][0] != 0:
            abort(403)


        # SEÇÃO PARA ATUALIZAR A SOLICITAÇÃO
        userId = str(current_user.id)

        engine = get_engine('jdt')
        with engine.connect() as cnnx:

            if received_data['type'] == 'approve':
            
                if current_user.admin:
                    query = f"""UPDATE JDT_REQUEST_STOPCHANGES SET 
                                    approver1 = '{userId}', 
                                    approver2 = '{userId}', 
                                    approverStatus1 = 1, 
                                    approverStatus2 = 1,
                                    approverDate1 = GETDATE(),   
                                    approverDate2 = GETDATE()
                                WHERE 
                                    requestId = {received_data['requestId']}"""
                    cnnx.execute(text(query))

                else:

                    if userId == str(check_request['approver1'][0]):
                        query = f"""UPDATE JDT_REQUEST_STOPCHANGES SET 
                                        approverStatus1 = 1, 
                                        approverDate1 = GETDATE() 
                                    WHERE 
                                        requestId = {received_data['requestId']}"""
                        cnnx.execute(text(query))

                    if userId == str(check_request['approver2'][0]):
                        query = f"""UPDATE JDT_REQUEST_STOPCHANGES SET 
                                        approverStatus2 = 1, 
                                        approverDate2 = GETDATE() 
                                    WHERE 
                                        requestId = {received_data['requestId']}"""
                        cnnx.execute(text(query))
                
                cnnx.commit()
                    
                query = f"""SELECT 
                                TOP(1) T1.*, T2.workcenter, T2.logMinutes / 60.0 AS logHours
                            FROM JDT_REQUEST_STOPCHANGES T1
                                LEFT JOIN JDT_REQUEST_STOPCHANGES_PLEX T2 ON T1.eventId = T2.eventId
                            
                            WHERE requestId = {received_data['requestId']}"""
                check_request = pd.read_sql(query, cnnx)
                check_request = check_request.iloc[0]

                if not check_request['approverStatus1'] or not check_request['approverStatus2']:
                    return 'REQUEST APPROVED.', 200

                query = f"""UPDATE JDT_REQUEST_STOPCHANGES SET 
                                finalDate = GETDATE() 
                            WHERE 
                                requestId = '{received_data['requestId']}'"""
                cnnx.execute(text(query))

                if check_request['plex']:

                    status_key = {'Mão de Obra': 10779, 'Método': 222, 'Manutenção' : 213 , 'Material' : 10781, 'Movimentação' : 10780, 'Programada' : 10778}
                    
                    newMotivePlex = getPlex('events')[check_request['motive2'] == getPlex('events')['Code']].iloc[0]

                    payload = {
                        'inputs' : {
                            'Log_Key': f"{check_request['eventId'].astype(int)}"
                            , 'Workcenter_Event_Key' : f"{newMotivePlex['Workcenter_Event_Key']}"
                            , 'Workcenter_Key' : f"{check_request['workcenter']}"
                            , 'Workcenter_Status_Key' : f"{status_key[newMotivePlex['Workcenter_Event_Group']]}"
                            , 'Log_Hours': check_request['logHours']
                            , 'Reviewed': 1
                        }
                    }

                    response = POST_WITH_AUTH("https://jost.on.plex.com/api/datasources/12272/execute", HTTPBasicAuth(MES_MAIN_USER, MES_MAIN_PASSWORD), payload)

                    if "errors" in response:
                        return 'PLEX ERROR.', 400

                else:
                    
                    engine_ftm = get_engine('ftm')
                    with engine_ftm.begin() as cnnx2:
                        query = f"""UPDATE [FTMETRICS_JOST].[dbo].OEEQEventHistory SET sEndVal = '{check_request['motive2']}' WHERE lOEEEventId = '{check_request['eventId'].astype(int)}'"""
                        cnnx2.execute(text(query))

                cnnx.commit()

                query = f"""SELECT companyEmail FROM JDT_USER_DETAILS WHERE id = '{check_request['requesterId']}'"""
                requesterEmail = pd.read_sql(query, cnnx)['companyEmail'][0]

                msg = Message(f"Alteração de Paradas - Solicitação {received_data['requestId']} aprovada",
                                sender=('Transformação Digital JOST', 'noreply.digitaljost@randon.com.br'),
                                recipients=[requesterEmail])

                msg.html = render_template('request.stopChanges/stopChanges_email_approved.html',
                                        requestId=received_data['requestId'],
                                        requestText=check_request['requestText'])
                mail.send(msg)

                return 'REQUEST APPROVED.', 200

            else:

                if userId == str(check_request['approver1'][0]):
                    query = f"""UPDATE JDT_REQUEST_STOPCHANGES SET 
                                    approverStatus1 = 2, 
                                    deniedText = '{received_data['deniedText']}',
                                    approverDate1 = GETDATE(),
                                    finalDate = GETDATE()  
                                WHERE 
                                    requestId = {received_data['requestId']}"""
                    cnnx.execute(text(query))

                elif userId == str(check_request['approver2'][0]):
                    query = f"""UPDATE JDT_REQUEST_STOPCHANGES SET 
                                    approverStatus2 = 2, 
                                    deniedText = '{received_data['deniedText']}',
                                    approverDate2 = GETDATE(),
                                    finalDate = GETDATE()  
                                WHERE 
                                    requestId = {received_data['requestId']}"""
                    cnnx.execute(text(query))

                elif current_user.admin:
                    query = f"""UPDATE JDT_REQUEST_STOPCHANGES SET 
                                    approver1 = '{userId}', 
                                    approver2 = '{userId}', 
                                    approverStatus1 = 2, 
                                    approverStatus2 = 2, 
                                    deniedText = '{received_data['deniedText']}', 
                                    approverDate1 = GETDATE(),   
                                    approverDate2 = GETDATE(),
                                    finalDate = GETDATE()
                                WHERE 
                                    requestId = {received_data['requestId']}"""
                    cnnx.execute(text(query))


                query = f"""SELECT companyEmail FROM JDT_USER_DETAILS WHERE id = '{check_request['requesterId'][0]}'"""
                requesterEmail = pd.read_sql(query, cnnx)['companyEmail'][0]

                msg = Message(f"Alteração de Paradas - Solicitação {received_data['requestId']} recusada",
                                sender=('Transformação Digital JOST', 'noreply.digitaljost@randon.com.br'),
                                recipients=[requesterEmail])

                msg.html = render_template('request.stopChanges/stopChanges_email_denied.html',
                                            requestId=received_data['requestId'],
                                            approverName=current_user.name,
                                            deniedText=received_data['deniedText'],
                                            requestText=check_request['requestText'][0])
                mail.send(msg)
                cnnx.commit()

                return 'REQUEST DENIED.', 200


# ROTA PARA CONSULTAR OS GRÁFICOS DE ALTERAÇÃO DE PARARADAS
@request_workcentersLogChange_bp.route('/oee/paradas/alterar/dash')
def stopChanges_dash():
    return render_template('general_maintenance.html')

    query = "SELECT NOME_MAQUINA as Name FROM CONFIG_TABLET WHERE FL_ATIVO = 1"
    mic_workcenters = engine_run_query(query, 'ftm')

    mes_workcenters = getPlex('workcenters')[['Name']]
    workcenters = pd.concat([mic_workcenters, mes_workcenters])

    return render_template('request.stopChanges/stopChanges_dash.html', 
                            events=getPlex('events').sort_values(by='Description').to_dict(orient='records'), 
                            workcenters=workcenters.to_dict(orient='records'))

# ROTA PARA PEGAR OS DADOS DOS GRÁFICOS
@request_workcentersLogChange_bp.route('/oee/paradas/alterar/dash_callback', methods=['POST'])
def dash_callback():
    return render_template('general_maintenance.html')

    received_data = request.get_json()

    conditions = []

    def add_filter(field_name, column_name, conditions):
        local_filter = received_data.get(field_name)
        if local_filter:
            filter_list = ', '.join(f"'{w}'" for w in local_filter)
            conditions.append(f"{column_name} IN ({filter_list})")

    add_filter('m_old', 'T3.CATEGORIA', conditions)
    add_filter('m_new', 'T4.CATEGORIA', conditions)
    add_filter('event_old', 'T1.motive1', conditions)
    add_filter('event_new', 'T1.motive2', conditions)

    main_where_clause = f"AND {' AND '.join(conditions)}" if conditions else ""

    conditions = []
    add_filter('workcenters', 'sDescription', conditions)
    workcenter_where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""

    query = f""" 
                WITH
                    EVENTS AS (
                        SELECT
                            lOEEEventId,
                            sDescription
                        FROM
                            [FTMETRICS_JOST].[dbo].OEEQEventHistory 
                        {workcenter_where_clause}

                    ),
                    STOPS AS (
                        SELECT
                            CATEGORIA,
                            CASE
                                WHEN MOTIVO = 'Sem Justificativa' THEN MOTIVO
                                ELSE SUBSTRING(MOTIVO, 5, LEN(MOTIVO))
                            END AS MOTIVO
                        FROM
                            [FTMETRICS_JOST].[dbo].CADASTRO_PARADA
                    ),
                    REQUESTS AS (
                        SELECT
                            eventId,
                            CASE
                                WHEN motive1 = 'Sem Justificativa' THEN motive1
                                ELSE SUBSTRING(motive1, 5, LEN(motive1))
                            END AS motive1,
                            CASE
                                WHEN motive2 = 'Sem Justificativa' THEN motive2
                                ELSE SUBSTRING(motive2, 5, LEN(motive2))
                            END AS motive2,
                            DATEDIFF(SECOND, openDate, CASE WHEN finalDate IS NULL
                                THEN GETDATE()
                                ELSE finalDate
                                END) AS duration,
                            openDate,
                            approverStatus1,
                            approverStatus2
                        FROM JDT_REQUEST_STOPCHANGES
                    )
                
                SELECT
                    T1.motive1,
                    T1.motive2,
                    T1.duration,
                    T3.CATEGORIA AS m_1,
                    T4.CATEGORIA AS m_2,
                    T2.sDescription,

                    CASE 
                        WHEN (approverStatus1 = 1 AND approverStatus2 = 1) THEN 'Aprovada'
                        WHEN (approverStatus1 = 2 OR approverStatus2 = 2) THEN 'Reprovada'
                        ELSE 'Aguardando'
                    END AS status

                FROM REQUESTS AS T1
                    JOIN EVENTS AS T2 ON T2.lOEEEventId = T1.eventId
                    JOIN STOPS AS T3 ON T3.MOTIVO = T1.motive1
                    JOIN STOPS AS T4 ON T4.MOTIVO = T1.motive2

                WHERE
                    T1.openDate BETWEEN '{received_data['start_date']}' AND '{received_data['end_date']}'
                    {main_where_clause}
            """
    
    data = pd.read_sql(query, cnnx)
    data = data[data['status'].astype(str).isin(received_data['status'])]

    events_by_motive = data.groupby(['motive1', 'motive2']).size().reset_index(name='QTT')
    m_1 = data['m_1'].value_counts().reset_index().rename(columns={'m_1': 'LABELS', 'count': 'QTT'})
    m_2 = data['m_2'].value_counts().reset_index().rename(columns={'m_2': 'LABELS', 'count': 'QTT'})

    total_requests = data.shape[0]

    def seconds_to_dhms(seconds):
        days = seconds // (24 * 3600)
        seconds = seconds % (24 * 3600)
        hours = seconds // 3600
        seconds %= 3600
        minutes = seconds // 60
        seconds %= 60
        return f'{days}d {hours}h {minutes}m {seconds}s'

    def aggregate_durations(group):
        return pd.Series({
            'max': seconds_to_dhms(group['duration'].max()),
            'min': seconds_to_dhms(group['duration'].min()),
            'mean': seconds_to_dhms(int(group['duration'].mean())),
            'count': group['duration'].count()
        })

    if data.empty:
        table = pd.DataFrame(columns=['motive1', 'motive2', 'sDescription', 'max', 'min', 'mean', 'count'])
    else:
        table = data.groupby(['motive1', 'motive2', 'sDescription']).apply(aggregate_durations).reset_index()

    data_to_send = {
        'barChart1': events_by_motive.to_json(orient='records'),
        'pieChart1': m_1.to_json(orient='records'),
        'pieChart2': m_2.to_json(orient='records'),
        'totalRequests': str(total_requests),
        'table': table.to_json(orient='records')
    }

    return data_to_send
