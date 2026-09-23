"""Consulta dos apontamentos deixados na troca de turno."""

from app.utils.db_utils import engine_run_query


def get_shift_handoffs(selected_date):
    query = """
        EXEC [JOST_INTEGRATION_PRD].[dbo].[TD_OEE_ObterApontamentosDeixadosPorTurno]
            @data_referencia = :data_referencia
    """
    result = engine_run_query(query, 'plex', {'data_referencia': selected_date.isoformat()})
    quantity_column = (
        'apontamentos_deixados'
        if 'apontamentos_deixados' in result.columns
        else 'soma_current_counter'
    )

    return [
        {
            'turno_que_deixou': row['turno_que_deixou'],
            'workcenter': row['workcenter'],
            'apontamentos_deixados': int(row[quantity_column]),
        }
        for row in result.to_dict('records')
    ]
