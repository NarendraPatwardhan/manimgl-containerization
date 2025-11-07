run:
	docker run -it --rm \
		-v ./main.py:/app/main.py \
		-v ./videos:/app/videos \
		-v ./run.py:/app/run.py \
		manim python run.py
