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

hiku-proto:
	rm -rf dist/proto
	mkdir -p dist/proto
	python -m grpc_tools.protoc -I. --python_out=dist/proto hiku/protobuf/query.proto
	cp hiku/__init__.py dist/proto/hiku
	touch dist/proto/hiku/protobuf/__init__.py
	cp hiku/protobuf/query.proto dist/proto/hiku/protobuf
	cp MANIFEST.in dist/proto
	cp setup.proto.py dist/proto/setup.py
	cd dist/proto; python setup.py sdist -d ..; cd ../..
