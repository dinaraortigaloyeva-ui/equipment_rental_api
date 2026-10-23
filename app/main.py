"""Equipment Rental API: asosiy kirish nuqtasi."""

from fastapi import FastAPI

from app.routers import auth, equipment, rentals, admin, users

app = FastAPI(
    title="Equipment Rental API",
    description="Kamera, proyektor va boshqa jihozlarni kunlik ijaraga berish API si.",
    version="1.0.0",
)

app.include_router(auth.router)
app.include_router(equipment.router)
app.include_router(rentals.router)
app.include_router(admin.router)
app.include_router(users.router)

@app.get("/", tags=["Root"])
def root():
    return {"message": "Equipment Rental API ishlayapti. Hujjatlar: /docs"}

@app.get("/health", tags=["Health"])
def health_check():
    return {"status": "ok"}