print "hello, world\n"
puts "foo bar baz"
p! "holla", typeof("holla")

message = "foo hoo"
puts message
p! message, typeof(message)

message = 0b010101
puts message
p! message, typeof(message)

check_int = 1e12
p! check_int, typeof(check_int)
p! check_int.to_i64, typeof(check_int.to_i64)

def life_universe_and_everything : Int32
  return 42
  "Fortytwo"
end

puts life_universe_and_everything + 1

puts "----------------------------------------"

class String
  def longest_repetition?
    max = chars
      .chunk { |chunk_x| p! chunk_x, typeof(chunk_x); chunk_x }
      .max_by { |max_by_x| p! max_by_x; max_by_x.last.size }

    p! max
    {max.first, max.last.size} if max
  end
end

puts "aaabb".longest_repetition? # => {'a', 3}

puts "----------------------------------------"

module EntryMod
  alias ValType = String | Int32 | Float64

  class Entry
    property value : ValType?

    def initialize(value : ValType? = nil)
      @entries = {} of String => self
      @value = value
    end

    def [](key : String)
      @entries[key] ||= Entry.new
    end

    def []=(key : String, value : ValType)
      self[key].value = value
    end

    def inspect(io)
      io << "Entry.new(#{@value})"
    end

    def to_s(io)
      io << value
    end
  end
end

e = EntryMod::Entry.new
e["foo"]["bar"]["int"] = "1"
e["foo"]["bar"]["str"] = "foo"
e["foo"]["bar"] = "1"
e["foo"]["bar"] = 99

p! e["foo"]["bar"]["int"]
p! e["foo"]["bar"]

require "spec"

describe "Entry" do
  it "should allow nested values" do
    e = EntryMod::Entry.new
    e["foo"]["bar"] = "1"

    e["foo"]["bar"].value.should eq "1"

    e["foo"]["bar"] = "foo"
    e["foo"]["baz"] = "foo"
    e["foo"] = 3

    e["foo"].value.should eq 3
    e["foo"]["baz"].value.should eq "foo"
    e["foo"]["bar"].value.should eq "foo"
  end
end
