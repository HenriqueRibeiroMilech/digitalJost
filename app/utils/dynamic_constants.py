"""
    Módulo dynamic_constants
    -----------------------
    Gerencia dados de referência do Plex (workcenters, events) com atualização automática em background.

    - Os dados são atualizados por um thread em intervalos definidos (ex.: 4 horas).
    - Todos os acessos usam o cache, garantindo alta eficiência para múltiplos acessos simultâneos.
    - O acesso é thread-safe e nunca dispara múltiplas consultas ao banco em paralelo.

    Classes:
        PlexDataManager: Gerencia o cache e atualização dos dados Plex.
    Funções:
        getPlex(tipo): Retorna o DataFrame do tipo solicitado ('workcenters' ou 'events'), sempre do cache.
"""

import pandas as pd
import time
import threading

from app.utils.db_utils import get_engine


class PlexDataManager:
    """
    Gerencia dados de referência do Plex (workcenters, events) com atualização automática em background.

    - Os dados são atualizados por um thread em intervalos definidos (ex.: 4 horas).
    - Todos os acessos usam o cache, garantindo alta eficiência para múltiplos acessos simultâneos.
    - O acesso é thread-safe e nunca dispara múltiplas consultas ao banco em paralelo.

    Atributos:
        _cache (dict): Cache dos DataFrames ('workcenters', 'events').
        _interval (int): Intervalo de atualização em segundos.
        _lock (threading.Lock): Lock para acesso thread-safe ao cache.
        _thread (threading.Thread): Thread de atualização automática dos dados.
    Métodos:
        get(tipo): Retorna o DataFrame do tipo solicitado ('workcenters' ou 'events'), sempre do cache.
    """

    def __init__(self):
        self._cache = {
            'workcenters': None,
            'events': None
        }
        self._interval = 4 * 60 * 60
        self._lock = threading.Lock()
        self._thread = threading.Thread(target=self._scheduler, daemon=True)
        self._thread.start()

    def _scheduler(self):
        while True:
            try:
                with self._lock:
                    self._cache['workcenters'] = self._get_workcenters()
                    self._cache['events'] = self._get_events()
            except Exception as e:
                # Log de erro opcional
                print(f"Erro ao atualizar cache PlexDataManager: {e}")
            time.sleep(self._interval)

    def _get_workcenters(self):

        engine = get_engine('plex')
        with engine.connect() as cnnx:
            query = f"""SELECT 
                    Workcenter_Code
                    , Workcenter_Group
                    , Workcenter_Key
                    , Name
                    , CAST(Active AS BIT) AS Active
                    FROM OPENQUERY([PLEX_DSN_JOST], '
                        SELECT 
                        Workcenter_Code
                        , Workcenter_Group
                        , Workcenter_Key
                        , Name
                        , Active
                        FROM Part_v_Workcenter')"""
            data = pd.read_sql(query, cnnx)

        data = data[~data['Workcenter_Code'].isin([
            "Mach2_Backup", "Mach2_Backup2", "BRO_2310", "C06", "ELE_01", "FER_01", "FER_02", "GARANTIA", "INSFINAL"
            , "L04", "LABORAT", "M16", "M20", "MEC_01", "PT01", "S03", "S04", "S05", "S06", 'E01_Obsoleto'
            , "S12", "S14", "S19", "S22", "S24", "S25", "S26", "S27", "S28", "S29", "S30"
            , "S31", "S32", "S33", "S35", "SUBCON", "T01", "T02", "T09", "TER_01", "TER_02", "TER_03"
        ])]
        return data

    def _get_events(self):
        engine = get_engine('plex')
        with engine.connect() as cnnx:
            query = f"""
                SELECT Workcenter_Event_Key, Description, Workcenter_Event_Group, Active, Code 
                FROM OPENQUERY([PLEX_DSN_JOST], 'SELECT Workcenter_Event_Key, Description, Workcenter_Event_Group, Active, Code FROM Part_v_Workcenter_Event WHERE Code != ''''')
            """
            data = pd.read_sql(query, cnnx)
        return data

    def get(self, value):
        value = value.lower()
        if value not in self._cache:
            raise ValueError(f"Tipo inválido: {value}. Use 'workcenters' ou 'events'.")
        with self._lock:
            # Retorna sempre o cache atual
            if self._cache[value] is None:
                # Inicializa na primeira chamada
                if value == 'workcenters':
                    self._cache[value] = self._get_workcenters()
                elif value == 'events':
                    self._cache[value] = self._get_events()
            return self._cache[value].copy()

# Instância única do gerenciador de dados Plex
_plex_data_manager = PlexDataManager()

def getPlex(value):
    """Obtém dados Plex do tipo solicitado ('workcenters' ou 'events'), com cache automático."""
    return _plex_data_manager.get(value)
