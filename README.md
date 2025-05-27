start by building it:
## Build and run with Docker Compose
docker-compose up --build

## Or run locally for development
cd gongle-web
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

## Trun the development server:
python app.py

## hten you can open actual webpage at for dev:
Open [http://localhost:3000](http://localhost:3000) with your browser to see the result.

