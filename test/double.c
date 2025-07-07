static inline int bar(int a, int b) {
	return a - b;
}


static inline int foo(int a, int b) {
	return a + b;
}

int main() {
	int x = foo(1, 4);
	return x;
}
