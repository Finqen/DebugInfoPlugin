inline int bar(int a, int b) {
	return a - b;
}


inline int foo(int a, int b) {
	return a + b;
}

void baz() {
	int x = bar(3,2);
	int y = foo(2,3);
}

int main() {
	baz();
	return 0;
}
