from ecommerce_price_prediction import SessionLocal, Product
db = SessionLocal()
products = db.query(Product).limit(10).all()
for p in products:
    print(f"ID: {p.id} | Name: {p.name} | Image: {p.image_url}")
db.close()
