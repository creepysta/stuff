sealed trait SegmentTree
case class Leaf(value: Int) extends SegmentTree
case class Node(start: Int, end: Int, left: SegmentTree, right: SegmentTree) extends SegmentTree

def build(xs: List[Int]): SegmentTree = {
  def buildRec(l: Int, r: Int): SegmentTree = {
    if (l == r) Leaf(xs(l))
    else {
      val m = (l + r) / 2
      Node(l, r, buildRec(l, m), buildRec(m + 1, r))
    }
  }
  buildRec(0, xs.length - 1)
}

def query(t: SegmentTree, l: Int, r: Int)(f: (Int, Int) => Int)(e: Int): Int = {
  def queryRec(t: SegmentTree): Int = t match {
    case Leaf(x) => x
    case Node(tl, tr, left, right) =>
      if (r < tl || tr < l) e
      else if (l <= tl && tr <= r) f(queryRec(left), queryRec(right))
      else f(queryRec(left), queryRec(right))
  }
  queryRec(t)
}

def update(t: SegmentTree, i: Int, x: Int): SegmentTree = {
  def updateRec(t: SegmentTree): SegmentTree = t match {
    case Leaf(_) => Leaf(x)
    case Node(tl, tr, left, right) =>
      if (i < tl || tr < i) t
      else {
        val m = (tl + tr) / 2
        val left2 = updateRec(left)
        val right2 = updateRec(right)
        Node(tl, tr, left2, right2)
      }
  }
  updateRec(t)
}

object HelloWorld {

  def main(args: Array[String]): Unit = {
    val xs = List(1, 3, 5, 7, 9, 11)
    val t = build(xs)

    // Query the sum of the elements in the range [1, 3]
    val sum1 = query(t, 1, 3)(_ + _)(0)
    println(sum1) // 15

    // Update the value at index 2 to 6
    val t2 = update(t, 2, 6)

    // Query the sum of the elements in the range [1, 3] again
    val sum2 = query(t2, 1, 3)(_ + _)(0)
    println(sum2) // 16

  }
}
