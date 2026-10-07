from apiflask import APIBlueprint

from .schemas import EventCreate, EventList, EventOut, EventQuery

# Adicione aqui os imports reais dos mecanismos da etapa 7.1.
# current_actor e get_events_service precisam estar implementados.

events_bp = APIBlueprint(
    "events",
    __name__,
    url_prefix="/api/v1/events",
)


@events_bp.get("")
@events_bp.input(EventQuery, location="query")
@events_bp.output(EventList)
def list_events(query_data):
    return get_events_service().list(query_data, current_actor())


@events_bp.post("")
@events_bp.input(EventCreate)
@events_bp.output(EventOut, status_code=201)
def create_event(json_data):
    return get_events_service().create(json_data, current_actor())