from app.schemas import IncidentCreate
def test_incident_contract():
    x=IncidentCreate(service="checkout",severity="SEV2",summary="latency")
    assert x.severity=="SEV2"
