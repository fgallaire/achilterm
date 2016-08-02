build:
	true

install:
	install -d "%(bin)s"
	install -d "%(lib)s"
	install achilterm.bin "%(bin)s/achilterm"
	install achilterm.initd "%(etc)s/init.d/achilterm"
	install -m 644 achilterm.css achilterm.html achilterm.js achiltermlite.css achiltermlite.html achiltermlite.js "%(lib)s"
	install -m 755 achilterm.py "%(lib)s"
	gzip --best -c achilterm.1 > achilterm.1.gz
	install -d "%(man)s"
	install achilterm.1.gz "%(man)s"

clean:
	rm achilterm.bin
	rm achilterm.initd
	rm achilterm.1.gz
	rm Makefile

