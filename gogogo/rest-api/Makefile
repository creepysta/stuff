
run:
	@docker run -it --rm -v $(shell pwd):/app --workdir /app -p 8000:80 golang:alpine3.16 sh

test:
	@CGO_ENABLED=0 GO111MODULE=on go test .

build:
	@go build -o /go/bin .
