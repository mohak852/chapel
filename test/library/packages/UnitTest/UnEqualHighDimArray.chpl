use UnitTest;
var x : [1..5,1..7] real;
var y : [{1..5,1..7}] int;
UnitTest.assertEqual(x,y);