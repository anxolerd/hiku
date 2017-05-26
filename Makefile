__default__:
	@echo "Please specify a target to make"

proto:
	python -m grpc_tools.protoc -I. --python_out=. hiku/protobuf/query.proto
	python -m grpc_tools.protoc -I. --python_out=. tests/protobuf/result.proto
	python -m grpc_tools.protoc -I. --python_out=. docs/example.proto

release:
	./scripts/release_check.sh
	rm hiku/console/assets/*.js
	pi build static
	python setup.py sdist
