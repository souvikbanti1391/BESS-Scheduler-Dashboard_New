from fastapi import FastAPI
from routers.predict import router as predict_router
from routers.schedule import router as schedule_router

app = FastAPI(title="BESS Optimiser API")

@app.get('/')
def root():
    return {'status':'ok','message':'BESS Optimiser Backend'}

app.include_router(predict_router,prefix='/predict')
app.include_router(schedule_router,prefix='/schedule')
