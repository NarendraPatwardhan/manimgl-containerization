run:
	docker run -it --rm \
		-v ./main.py:/app/main.py \
		-v ./videos:/app/videos \
		-v ./run.sh:/app/run.sh \
		manim ./run.sh
