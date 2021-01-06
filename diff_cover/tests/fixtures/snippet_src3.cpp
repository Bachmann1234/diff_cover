#include <iostream>

void UselessFunction()
{
    // this is line 5
    printf("Test");

    // this is line 8
    printf("Test2");

    // this is line 11
    printf("Test");
}

int main()
{
    std::cout << "Hello World!";
    UselessFunction();
    return 0;
}
