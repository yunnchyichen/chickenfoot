'''
Unit tests for chickenfoot.py

Run this with nose: $ nosetests

If you want to run a single test, try: nosetests test_chickenfoot:ClassName.method_name
'''

# std lib imports
import collections
import random
import types
import unittest


# code under test
import chickenfoot

class MockContext(object):
	'''
	A context manager that replaces an attribute on entry, and restores it on exit.
	Suitable for mocking module methods and anything without a 'self'
	'''
	def __init__(self, obj, attr, repl):
		'''
		* obj - object in which to replace an attribute
		* attr - name of the attribute to replace
		* repl - replacement value
		'''
		self.obj = obj
		self.attr = attr
		self.repl = repl
	
	def __enter__(self):
		'''
		Do the replacement when entering this context
		'''
		self.orig = getattr(self.obj, self.attr)
		setattr(self.obj, self.attr, self.repl)
		return self

	def __exit__(self, exc_type, exc_val, tb):
		'''
		Restore the original when exiting the context

		Don't suppress exceptions
		'''
		setattr(self.obj, self.attr, self.orig)


class FactorialCombinationsTest(unittest.TestCase):
	def test_factorial_combinations(self):
		'''
		factorial_combinations: produces tuples as expected
		'''
		actual = list(chickenfoot.factorial_combinations(1))
		self.assertEquals([(0, 0), (0, 1), (1, 1)], actual)

		actual = list(chickenfoot.factorial_combinations(2))
		self.assertEquals([(0, 0), (0, 1), (1, 1), (0, 2), (1, 2), (2, 2)], actual)

class NodeTest(unittest.TestCase):
	def test_leaves(self):
		'''
		Node.leaves: correctly determines leaf nodes
		'''
		# make the topmost tile (9, 9)
		tile = chickenfoot.Tile(9, 9)
		root = chickenfoot.Root(tile)

		# no children; root tile should be the only leaf
		self.assertEquals([root], [i for i in root.leaves])

		# we'll build a first row of tiles (9, 1) and (9, 2)
		# call this "Row A"
		childA1 = root.add_child(chickenfoot.Tile(9, 1))
		self.assertEquals([childA1], [i for i in root.leaves])

		# add another child
		childA2 = root.add_child(chickenfoot.Tile(9, 2))
		self.assertEquals([childA1, childA2], [i for i in root.leaves])

		# add (1, 0) to childA1, and add (2, 3) to childA2
		# call this "row B"
		childB1 = childA1.add_child(chickenfoot.Tile(1, 0))
		childB2 = childA2.add_child(chickenfoot.Tile(2, 3))
		
		# only childrenB nodes should be leaves
		self.assertEquals([childB1, childB2], [i for i in root.leaves])

	def test_bottom(self):
		'''
		Node.bottom: provides 'a' when in normal orientation, and 'b' when inverted
		'''
		tile = chickenfoot.Tile(1, 2)
		root = chickenfoot.Root(tile)
		self.assertEquals(2, root.bottom)

		root.orientation = chickenfoot.Orientation.INVERTED
		self.assertEquals(1, root.bottom)

	def test_add_child(self):
		'''
		Node.add_child: accepts up to a maximum number of child nodes
		'''
		root = chickenfoot.Root(chickenfoot.Tile(6, 6))

		# add four children
		children = [root.add_child(chickenfoot.Tile(6, i)) for i in range(4)]
		self.assertEquals(children, root.children)

		# attempting to add a fifth child raises NodeFullException
		self.assertRaises(chickenfoot.NodeFullException, root.add_child, chickenfoot.Tile(5, 6))

		# attempting to add a mismatched child raises ValueError
		root = chickenfoot.Root(chickenfoot.Tile(6, 6))
		self.assertRaises(ValueError, root.add_child, chickenfoot.Tile(1, 2))

	def test_find_attach_position(self):
		'''
		Node.find_attach_position: finds at least one subtree when applicable,
		and raises ValueError otherwise.
		'''
		tile = chickenfoot.Tile(6, 6)
		root = chickenfoot.Root(tile)
		
		# asking for an attachment place for the root should be possible
		self.assertEquals(root, root.find_attach_position(chickenfoot.Tile(1, 6)))
		
		# add two children: (1, 6) and (2, 6)
		children = [root.add_child(chickenfoot.Tile(i, 6)) for i in (1, 2)]
		
		# asking for an attachment point for (2, 2) should return the second child
		self.assertEqual(children[1], root.find_attach_position(chickenfoot.Tile(2, 2)))

		# asking for an attachment point for (3, 3) should raise ValueError
		self.assertRaises(ValueError, root.find_attach_position, chickenfoot.Tile(3, 3))

class GameTest(unittest.TestCase):
	def test_setup_player_hands(self):
		'''
		Game._setup_player_hands: players get the expected number of tiles
		'''
		p1 = chickenfoot.Player('p1')
		game = chickenfoot.Game(6, 6, 4, [p1])
		game._setup_player_hands()
		self.assertEquals(4, len(p1.hand))

	def test_root_tile_turn_found(self):
		'''
		Game._root_tile_turn: produces a table with a root tile when one player has the tile in their hand
		'''
		# create two players
		p1 = chickenfoot.Player('p1')
		p2 = chickenfoot.Player('p2')
		# give p1 some tiles that don't include the root
		p1.hand = [chickenfoot.Tile(1, 1), chickenfoot.Tile(2, 2), chickenfoot.Tile(3, 3)]
		# give p2 the root tile (and some others)
		p2.hand = [chickenfoot.Tile(1, 2), chickenfoot.Tile(3, 4), chickenfoot.Tile(9, 9)]

		# create the game and run the turn
		game = chickenfoot.Game(9, 9, 7, [p1, p2])
		game._root_tile_turn()

		# assert that the expected root tile got picked
		root_tile = game.root.tile
		self.assertEquals((9, 9), game.root.tile.ends)

		# assert hand sizes
		self.assertEquals(3, len(p1.hand))
		self.assertEquals(2, len(p2.hand))

	def test_root_tile_turn_not_found(self):
		'''
		Game._root_tile_turn: produces an empty table and forces players to draw when the root tile isn't found
		'''
		# create two players
		p1 = chickenfoot.Player('p1')
		p2 = chickenfoot.Player('p2')
		# give p1 and p2 some tiles that don't include the root
		p1.hand = [chickenfoot.Tile(1, 1), chickenfoot.Tile(2, 2), chickenfoot.Tile(3, 3)]
		p2.hand = [chickenfoot.Tile(1, 2), chickenfoot.Tile(3, 4), chickenfoot.Tile(5, 6)]

		# create the game and run the turn
		game = chickenfoot.Game(9, 9, 7, [p1, p2])
		game._root_tile_turn()

		# assert that the expected root tile did not get added
		self.assertEquals(None, game.root)

		# assert hand sizes
		self.assertEquals(4, len(p1.hand))
		self.assertEquals(4, len(p2.hand))

	def test_handle_play_root_to_open(self):
		'''
		Game._handle_play: switches to normal gameplay after all four arms of the root have been built
		'''
		# create a game
		game = chickenfoot.Game(1, 9, 7, [chickenfoot.Player('p1')])

		# skip to the state after the root has been found
		game.root = chickenfoot.Root(chickenfoot.Tile(9, 9))
		game.state = chickenfoot.Game.State.ROOT
		
		# add three tiles with 9s
		for i in range(3):
			game._handle_play(chickenfoot.Tile(1, 9), game.root)

		# we should still be in 'ROOT' state
		self.assertEquals(chickenfoot.Game.State.ROOT, game.state)

		# the root should now have three children
		self.assertEquals(3, len(game.root.children))

		# add a fourth tile
		game._handle_play(chickenfoot.Tile(1, 9), game.root)

		# game should have switched to 'OPEN' state
		self.assertEquals(None, game.current_chickie)
		self.assertEquals(chickenfoot.Game.State.OPEN, game.state)
		self.assertEquals(4, len(game.root.children))

	def test_handle_play_open_to_chickie(self):
		'''
		Game._handle_play: switches from normal play to restricted, "chickie" play
		'''
		# create a game
		game = chickenfoot.Game(1, 9, 7, [chickenfoot.Player('p1')])

		# skip to the state after the root has been found and all arms have been filled in
		game.root = chickenfoot.Root(chickenfoot.Tile(9, 9))
		for i in range(4):
			game.root.add_child(chickenfoot.Tile(9, 1))
		game.state = chickenfoot.Game.State.OPEN

		# play a double
		game._handle_play(chickenfoot.Tile(1, 1), game.root.children[0])

		# assert that the state switched and the new tile is attached
		self.assertEquals(game.root.children[0].children[0], game.current_chickie)
		self.assertEquals(chickenfoot.Game.State.CHICKIE, game.state)
		self.assertEquals(1, len(game.root.children[0].children))

	def test_handle_play_open_to_open(self):
		'''
		Game._handle_play: when in normal play, a non-double doesn't change the game state
		'''
		# create a game
		game = chickenfoot.Game(1, 9, 7, [chickenfoot.Player('p1')])

		# skip to the state after the root has been found and all arms have been filled in
		game.root = chickenfoot.Root(chickenfoot.Tile(9, 9))
		for i in range(4):
			game.root.add_child(chickenfoot.Tile(9, 1))
		game.state = chickenfoot.Game.State.OPEN

		# play a regular tile
		game._handle_play(chickenfoot.Tile(1, 2), game.root.children[0])

		# assert that the state switched and the new tile is attached
		self.assertEquals(None, game.current_chickie)
		self.assertEquals(chickenfoot.Game.State.OPEN, game.state)
		self.assertEquals(1, len(game.root.children[0].children))

	def test_handle_play_chickie_to_open(self):
		'''
		Game._handle_play: switches from "chickie" to normal play when a chickenfoot is completed
		'''
		# create a game
		game = chickenfoot.Game(1, 9, 7, [chickenfoot.Player('p1')])

		# skip to the state after the root has been found and all arms have been filled in
		game.root = chickenfoot.Root(chickenfoot.Tile(9, 9))
		for i in range(4):
			game.root.add_child(chickenfoot.Tile(9, 1))
			
		# add a chickenfoot child
		chickie_node = game.root.children[0].add_child(chickenfoot.Tile(1, 1))
		game.current_chickie = chickie_node
		game.state = chickenfoot.Game.State.CHICKIE

		# we're done setting up the state of the Game

		# play two tiles
		for i in range(2):
			game._handle_play(chickenfoot.Tile(1, 2), chickie_node)

		# assert that the state is still chickie, and there are two children
		self.assertEquals(chickenfoot.Game.State.CHICKIE, game.state)
		self.assertEquals(chickie_node, game.current_chickie)
		self.assertEquals(2, len(chickie_node.children))

		# add a third tile
		game._handle_play(chickenfoot.Tile(1, 3), chickie_node)

		# assert that the chickenfoot is closed
		self.assertEquals(chickenfoot.Game.State.OPEN, game.state)
		self.assertEquals(None, game.current_chickie)
		self.assertEquals(3, len(chickie_node.children))		

	def test_round_over_empty_hand(self):
		'''
		Game._round_over: one player with an empty hand
		'''
		# create a list of players and use it to make a game
		players = [chickenfoot.Player('p%d' % i) for i in range(4)]
		game = chickenfoot.Game(1, 9, 7, players)

		# we need to plant something on the board for _round_over to work
		game.root = chickenfoot.Root(chickenfoot.Tile(9, 9))

		# give all players some tiles
		game._setup_player_hands()

		# game should not be over
		self.assertFalse(game._round_over())

		# remove one player's tiles
		players[3].hand = []
		
		# player 4 has an empty hand, so the game should be over
		self.assertTrue(game._round_over())

	def test_round_over_no_opportunities(self):
		'''
		Game._round_over: nobody can make a play
		'''
		# create a list of players
		players = [chickenfoot.Player('p%d' % i) for i in range(4)]
		# make a game; required root (1, 1), double-9 set, 7-tile starting hands
		game = chickenfoot.Game(1, 9, 7, players)

		# we need to plant something on the board for _round_over to work
		game.root = chickenfoot.Root(chickenfoot.Tile(9, 9))

		# give all players a hand with only one tile: a double 1
		for player in players:
			player.hand = [chickenfoot.Tile(1, 1)]
		
		# empty the boneyard
		game.boneyard.tiles = []
		
		# no opportunities should exist for any player, and there are no tiles available to draw
		self.assertTrue(game._round_over())		
		
	def test_opportunities_open(self):
		'''
		Game._opportunities: finds playable tiles in "open" play
		'''
		# make a game; required root (1, 1), double-9 set, 7-tile starting hands, 1 player
		player = chickenfoot.Player('p1')
		game = chickenfoot.Game(1, 9, 7, [player])

		# tweak the game to skip past finding the root tile
		game.root = chickenfoot.Root(chickenfoot.Tile(9, 9))

		# give the player a hand of tiles, two of which are opportunities, and two of which aren't
		player.hand = [chickenfoot.Tile(1, 1), chickenfoot.Tile(2, 2), chickenfoot.Tile(9, 1), chickenfoot.Tile(2, 9)]

		# two of the tiles should be opportunities
		self.assertEquals(player.hand[2:], game._opportunities(player))

		# change the player's hand to have all invalid tiles
		player.hand = [chickenfoot.Tile(1, 1)]

		# the player should have no opportunities now
		self.assertEquals([], game._opportunities(player))

	def test_opportunities_chickie(self):
		'''
		Game._opportunities: only allows for plays under the chickenfoot during "chickie" play
		'''
		# make a game; required root (1, 1), double-9 set, 7-tile starting hands, 1 player
		player = chickenfoot.Player('p1')
		game = chickenfoot.Game(1, 9, 7, [player])

		# tweak the game to skip past finding the root tile
		game.root = chickenfoot.Root(chickenfoot.Tile(9, 9))

		# build the root's arms: (9, 0), (9, 1), (9, 2), and (9, 3)
		for i in range(4):
			game.root.add_child(chickenfoot.Tile(9, i))

		# add a (1, 1) under (9, 1) and set the game's state to CHICKIE
		chickie = game.root.children[1].add_child(chickenfoot.Tile(1, 1))
		game.state = game.State.CHICKIE
		game.current_chickie = chickie

		# give the player a hand with tiles that match all the exposed ends
		player.hand = [chickenfoot.Tile(i, i) for i in range(4)]

		# only the (1, 1) tile should be an opportunity
		self.assertEquals([player.hand[1]], game._opportunities(player))

	def test_opportunities_root(self):
		'''
		Game._opportunities: only allows for root arms to be added until the 4th is present
		'''
		# make a game; required root (1, 1), double-9 set, 7-tile starting hands, 1 player
		player = chickenfoot.Player('p1')
		game = chickenfoot.Game(1, 9, 7, [player])
		game.state = game.State.ROOT

		# tweak the game to skip past finding the root tile
		game.root = chickenfoot.Root(chickenfoot.Tile(9, 9))

		# give the player the following hand: (9, 0), (9, 1), (9, 2), (0, 0), (1, 1), (2, 2)
		player.hand = [chickenfoot.Tile(9, i) for i in range(3)] + [chickenfoot.Tile(i, i) for i in range(3)]

		# the (9, x) tiles are immediately opportunities
		self.assertEquals(player.hand[:3], game._opportunities(player))

		# add the (9, x) tiles to the board; the player now has only the double tiles
		for i in range(3): 
			game.root.add_child(player.fetch_tile(9, i))

		# there is one spot remaining in the root arm, but this player doesn't have any 9s
		# we shouldn't be allowed to attach to any of the leaf ends, even though that would 
		# be allowed in normal play
		self.assertEquals([], game._opportunities(player))

	def test_run_root_tile_turn(self):
		'''
		Game.run: invokes _root_tile_turn until self.root is assigned
		'''
		def _root_tile_turn(self):
			'a replacement for _root_tile_turn that must be called three times, and then sets a root.'
			if not hasattr(self, '_root_tile_turn_call_count'):
				self._root_tile_turn_call_count = 1
			else:
				self._root_tile_turn_call_count += 1
			
			if self._root_tile_turn_call_count == 3:
				self.root = chickenfoot.Root(chickenfoot.Tile(9, 9))
		def mock_cycle(bogus):
			'exit immediately'
			return []
		
		game = chickenfoot.Game(9, 9, 7, [chickenfoot.Player('p1')])

		# mock out game._root_tile_turn
		game._root_tile_turn = types.MethodType(_root_tile_turn, game)

		# mock out chickenfoot.cycle so we don't end up in an infinite loop
		with MockContext(chickenfoot, 'cycle', mock_cycle):
			game.run()

		# check that _root_tile_turn got called the expected number of times
		self.assertEquals(3, game._root_tile_turn_call_count)

	def test_run_one_player(self):
		'''
		Game.run: plays tiles correctly in a one-player game

		By carefully crafting a player's hand, we can guarantee the outcome of
		the round.  Mock out the player's initial draw, and then check that 
		'run' achieved the expected end of the game.
		'''
		# create an alias for the current instance - the TestCase - so we can
		# use it in mocks
		executing_test = self

		def mock_draw(self):
			'''
			safety net: in these scenarios, there should be no need to draw from
			the boneyard, and an attempt to do so is an indication of a problem.
			'''
			executing_test.fail('Attempted to draw from boneyard')

		def mock_setup_player_hands(self):
			'''
			give the only player a crafted hand, to be played in this order:
				(9, 9) - root tile
				(9, 1) - first arm
				(9, 2)
				(9, 3)
				(9, 4) - finishes root arms
				(1, 0) - one open play
			'''
			self.players[0].hand = [chickenfoot.Tile(a, b) for a, b in [(9, 9), (9, 1), (9, 2), (9, 3), (9, 4), (1, 0)]]
		
		game = chickenfoot.Game(9, 9, 7, [chickenfoot.MaxValuePlayer('p1')])

		# mock out game._setup_player_hands and Boneyard.draw
		game._setup_player_hands = types.MethodType(mock_setup_player_hands, game)
		game.boneyard.draw = types.MethodType(mock_draw, game.boneyard)

		game.run()

		# now assert that the first player has an empty hand, and that the tree 
		# is build as expected
		self.assertEquals([], game.players[0].hand)
		self.assertEquals((9, 9), game.root.tile.ends)
		self.assertEquals(1, len(game.root.children))
		self.assertEquals((9, 1), game.root.children[0].tile.ends)
		self.assertEquals(1, len(game.root.children[0].children))
		self.assertEquals((1, 0), game.root.children[0].children[0].tile.ends)
		self.assertEquals(0, len(game.root.children[0].children[0].children))

class TileTest(unittest.TestCase):
	def test_ends(self):
		'''
		Tile.ends: provides the pips for 'a' and 'b'
		'''
		tile = chickenfoot.Tile(1, 2)
		self.assertEquals((1, 2), tile.ends)

	def test_is_double(self):
		'''
		Tile.is_double: True when the ends are equal
		'''
		self.assertTrue(chickenfoot.Tile(3, 3).is_double)
		self.assertFalse(chickenfoot.Tile(1, 3).is_double)

	def test_value(self):
		'''
		Tile.value: returns the sum of pips, unless it's a double blank
		'''
		self.assertEquals(6, chickenfoot.Tile(3, 3).value)
		self.assertEquals(chickenfoot.DOUBLE_BLANK_SCORE, chickenfoot.Tile(0, 0).value)

class PlayerTest(unittest.TestCase):
	'Test Player, RandomPlayer, and MaxValuePlayer'

	def test_pick_tile(self):
		'Player.pick_tile: removes the tile chosen by _pick_tile'
		player = chickenfoot.Player('p1')
		# give the player a hand of known values
		player.hand = [1, 2, 3]
		# mock out the choosing method
		player._pick_tile = types.MethodType(lambda self, opportunities: 3, player)

		# allow the player to pick from any of their tiles
		self.assertEquals(3, player.pick_tile(player.hand))
		# ensure that the chosen option got removed
		self.assertEquals([1, 2], player.hand)

	def test_random_player(self):
		'RandomPlayer._pick_tile: chooses no one opportunity, out of a hundred given, more than 5 out of 20 tries'
		# build an ordered list 0-99
		opportunities = range(100)
		player = chickenfoot.RandomPlayer('your mom')

		# tally occurrences across 20 choices
		# using defaultdict with 'int' as its callable provides defaults of 0
		counts = collections.defaultdict(int)
		for choice in (player._pick_tile(opportunities) for i in range(20)):
			counts[choice] += 1

		# the most popular choice must have occurred less than 5 times
		self.assertLess(sorted(counts.values(), reverse=True)[0], 5)

	def test_max_value_player(self):
		'MaxValuePlayer._pick_tile: chooses the highest-value tile every time'
		# we'll build an ordered list 0-99, shuffle it, and make sure the player chooses 99 each of 20 times
		# note that MaxValuePlayer.pick_tile uses Tile.value, so we'll have to use a mock
		class MockTile(object):
			def __init__(self, value):
				self.value = value

		opportunities = [MockTile(i) for i in range(100)]
		player = chickenfoot.MaxValuePlayer('your other mom')

		for i in range(20):
			random.shuffle(opportunities)
			self.assertEquals(99, player._pick_tile(opportunities).value)
