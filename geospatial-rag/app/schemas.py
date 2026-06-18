from pydantic import BaseModel



class CloseSessionRequest(BaseModel):
    pass # we get session_id from path
