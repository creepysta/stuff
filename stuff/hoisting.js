var foo = 'foo';

function bar() {
    console.log("Outer bar");
    setTimeout(function () {
        console.log("setTimeout", foo)
    }, 0);
    console.log("1", foo);
    console.log("2", bar());
    console.log("3", foo);

    var foo = 'bar';
    function bar() {
        console.log("Inner bar");
        foo = 'bartwo';
    }
    console.log("4", foo);
}
bar();
console.log("5", foo);
    




// Outer bar
// 1 undefined
// Inner bar
// 2 undefined
// 3 bartwo
// 4 bar
// 5 foo
// setTimeout bar
