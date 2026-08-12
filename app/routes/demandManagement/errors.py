class DemandManagementError(Exception):
    status_code = 400


class ValidationError(DemandManagementError):
    pass


class NotFoundError(DemandManagementError):
    status_code = 404


class ConflictError(DemandManagementError):
    status_code = 409
