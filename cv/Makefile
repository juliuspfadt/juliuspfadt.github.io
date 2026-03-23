.PHONY: pdf watch clean

pdf: main.pdf

main.pdf: main.typ
	typst compile main.typ

watch:
	typst watch main.typ

clean:
	rm -f main.pdf
