lint:
	@black . && isort --profile black .

clear:
	@rm -rf store/

echo:
	@maelstrom test -w echo --bin echo.py --time-limit 5

generate:
	@maelstrom test -w unique-ids --bin generate.py --time-limit 10 --rate 1000 --node-count 3 --availability total --nemesis partition

broadcast_a:
	@maelstrom test -w broadcast --bin broadcast_a.py --node-count 1 --time-limit 20 --rate 10

broadcast_b:
	@maelstrom test -w broadcast --bin broadcast_b.py --node-count 5 --time-limit 20 --rate 10
