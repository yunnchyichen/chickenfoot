'''
"Chicken Foot" game simulation.

Using rules from here: http://www.pagat.com/tile/wdom/chickenfoot.html
'''

import operator
import random

# In this particular version of the game, the double blank is worth 50 points.
# I was introduced to the game with this rule included.
DOUBLE_BLANK_SCORE = 50

def factorial_combinations(max):
	'''
	Generate every permutation of tuples (a, b), such that a <= b and b <= max.
	(This kind of reminds me of n-factorial, but maybe that's just me)
	'''
	for b in range(max+1):
		for a in range(b+1):
			yield (a, b)

# todo: subclass list
class Boneyard(object):
	'The tiles from which players draw when they can\'t make a play'
	def __init__(self, set_size):
		'* set_size - domino sets are described in "double-X" sets, in which X is an integer.'
		self.tiles = [Tile(a, b) for a, b in factorial_combinations(set_size)]

	def draw(self):
		'Pick one tile from the boneyard randomly, remove it, and return it.'
		tile = random.choice(self.tiles)
		self.tiles.remove(tile)
		return tile

def cycle(iterable):
	'''
	infinite cycle, without making a copy (unlike itertools.cycle)

	TODO: think of a way to unit test this; I'm a little worried about mocking __builtin__.True
	'''
	while True:
		for i in iterable:
			yield i

def from_iterables(iterable):
	'''
	Generate each sub-element of every element of 'iterable'.

	Example: [(1, 2), (3, 4)] would yield 1, 2, 3, and 4.
	'''
	for i in iterable:
		for j in i:
			yield j

class Game(object):
	'''
	Store the state of the round in play, being the tiles on the field, in the boneyard, and in player's hands
	
	Dispatches to methods of the Player instances, so they can make decisions about which tiles to play.
	'''

	class State(object):
		'''
		Enumerate the states of the game:
		* ROOT - the four arms of the root must be filled
		* OPEN - any play may be made at the end of any arm
		* CHICKIE - a chicken foot must be completed before any other plays can be made
		'''
		ROOT, OPEN, CHICKIE = ('R', 'O', 'C')

	def __init__(self, required_root, set_size, starting_hand_size, players):
		'''
		* required_root - the number of pips that must be on the root double; this changes with each round
		* set_size - size of the set of dominoes we're playing with; e.g. 9 indicates a "double-9" set
		'''
		self.required_root = required_root
		self.boneyard = Boneyard(set_size)
		self.starting_hand_size = starting_hand_size
		self.players = players

		# some placeholders
		self._root = None
		self.state = None
		self.current_chickie = None

	@property
	def root(self):
		'''
		Simple getter for 'root'.  Defined only to make the @property decorator happy for the setter.
		'''
		return self._root

	@root.setter
	def root(self, root):
		'''
		Guarantees that whenever the root is assigned, it automatically gets "Normal" orientation
		'''
		self._root = root
		root.orientation = Orientation.NORMAL

	def run(self):
		'''
		Simulate running a game.
		'''
		# setup: everybody gets some tiles
		self._setup_player_hands()
		
		# first turn(s): find the root tile
		while not self.root:
			self._root_tile_turn()

		# set the first game state
		self.state = self.State.ROOT

		# player-by-player turns start now
		for player in cycle(self.players):
			# determine the subset of the player's hand that can be played
			opportunities = self._opportunities(player)

			print 'initial opportunities: %s' % [(tile.a, tile.b) for tile in opportunities]
	
			if not opportunities:
				# we're allowed to draw once
				drawn = self.boneyard.draw()
				if drawn: 
					# there was at least one pile in the boneyard;
					# add it to the player's hand and rebuild their opportunities
					player.add_tile(drawn)
					opportunities = self._opportunities(player)
			
			if opportunities:
				tile = player.pick_tile(opportunities)
				if self.state == self.State.CHICKIE:
					# must play to the chickenfoot in progress
					parent = self.current_chickie
				elif self.state == self.State.ROOT:
					# must attach an arm to the root
					parent = self.root
				else:
					# can attach at any leaf
					parent = self.root.find_attach_position(tile)
				
				# update internal state in reaction to the last play
				self._handle_play(tile, parent)
			
			if self._round_over():
				# this round of the game is over
				break

		# todo: score player's hands and return the results.
	
	def _handle_play(self, tile, parent):
		'''
		Update state in reaction to a tile being played.

		This handles transitions between various states:
		1) OPEN->CHICKIE if a double is played
		2) CHICKIE->OPEN if a chickenfoot is closed
		3) ROOT->OPEN if the fourth arm of the root is added
		'''
		# add the tile to the board
		child = parent.add_child(tile)

		# determine state transitions
		if self.state == self.State.ROOT and len(self.root.children) == 4:
			# we just closed the root
			self.state = self.State.OPEN
		elif tile.is_double:
			# the last play was a chickenfoot
			# we need to set up for the next player's turn
			self.state = self.State.CHICKIE
			self.current_chickie = child
		elif not tile.is_double and self.state == self.State.CHICKIE and len(self.current_chickie.children) == 3:
			# we just completed a chickenfoot, regular play resumes
			self.state = self.State.OPEN
			self.current_chickie = None

	def _round_over(self):
		'''
		return true if this round is finished.

		The game ends under two conditions:
		1) one player has an empty hand
		2) no players have any opportunities left, and the boneyard is empty
		'''
		# check for empty hands
		for player in self.players:
			if not player.hand:
				# this player has an empty hand
				return True
		
		# check for stalemate
		for player in self.players:
			if self._opportunities(player):
				# this player has at least one opportunity
				return False

		# optimization: could predict an early end to the game when the 
		# tiles in the boneyard won't yield anyone any new opportunities, but
		# that may actually be slower than just cycling through turns

		# no players had any opportunities; if the boneyard is empty, the game is over
		return self.boneyard.tiles == []

	def _setup_player_hands(self):
		'''
		Simulate players drawing their initial hands
		'''
		for player in self.players:
			for i in range(self.starting_hand_size):
				player.add_tile(self.boneyard.draw())
	
	def _root_tile_turn(self):
		'''
		Simulate a turn spent trying to find the root tile.

		Note that this turn is somewhat simultaneous; every player essentially 
		plays it at the same time, because either everybody draws, or 
		nobody draws, and the order of play is determined.
		'''
		for player in self.players:
			# each player gets a crack at finding the root tile
			tile = player.fetch_tile(self.required_root, self.required_root)
			if tile:
				# we found the starting tile
				
				# first, re-order self.players into the order of play
				# the player with the starting tile begins play; everybody else is randomly seated
				# this is a mild deviation from table-top play; usually nobody re-seats themselves
				self.players.remove(player)
				random.shuffle(self.players)
				self.players[0:0] = [player]

				# next, seed the board
				self.root = Root(tile)

				# skip the 'else'
				break
		else:
			# we did not find the starting tile
			# all players need to draw
			for i in self.players:
				i.add_tile(self.boneyard.draw())
			
	def _opportunities(self, player):
		'''
		Return an iterable of tiles that this player could play
		'''
		if self.state == self.State.CHICKIE:
			# opportunities limited to current chickie
			return [tile for tile in player.hand if self.current_chickie.tile.a in tile.ends]

		if self.state == self.State.ROOT:
			# leaves don't count when we're in root-filling mode
			return [tile for tile in player.hand if self.root.tile.a in tile.ends]

		# otherwise, any leaf can be used to make a play
		leaf_ends = set(from_iterables((i.tile.ends for i in self.root.leaves)))
		return [tile for tile in player.hand if leaf_ends & set([i for i in tile.ends])]

class Orientation(object):
	'''
	Normal: a tile has it's "a" facing "up," towards the root of the tree
	Inverted: a tile has it's "a" facing "down," away from the root of the tree
	'''
	NORMAL, INVERTED = ('N', 'I')

class NodeFullException(Exception):
	'''
	Raised by Node.add_child
	'''
	pass

class Node(object):
	'''
	Represents a node in the tree of the playing field.

	Every tile gets added to a node when it's played onto the table.
	Nodes add to the tile the concepts of an orientation and child nodes.
	'''
	def __init__(self, tile, max_children, orientation):
		self.children = []
		self.tile = tile
		self.max_children = max_children
		self.orientation = orientation

	def add_child(self, tile):
		'''
		Given a tile, build a new child Node instance to hold it, and attach it 
		under self.

		This assigns the new Node's max_children to be either 1 (if it's a regular tile),
		or 3 (if it's a double).  It also determines the node's orientation.

		Raises NodeFullException if there's no more room in the current node.
		Raises ValueError if neither of the ends of the tile match our bottom.

		Returns the newly created Node.
		'''
		# check to see if we're full
		if len(self.children) == self.max_children:
			raise NodeFullException

		if self.bottom not in tile.ends:
			# this tile doesn't have an end that matches our lowest end
			raise ValueError('Attempted to attach %s to a %s' % (tile, self.bottom))
		
		# add this to the list of children
		child = Node(
			tile, 
			1 if not tile.is_double else 3, 
			Orientation.NORMAL if self.bottom == tile.a else Orientation.INVERTED
		)
		self.children.append(child)
		return child

	@property
	def leaves(self):
		'''
		Generate Node instances at the bottom ends of the tree
		'''
		if self.children:
			for i in (i.leaves for i in self.children):
				# i is each child's generator; an iterable of nodes
				# we must unwind its generators in order to flatten out the result
				# todo: doesn't this kill some of the efficiency of generators?
				for j in i:
					yield j
		else:
			# we're a leaf
			yield self
	
	@property
	def bottom(self):
		'''
		Return the number of pips on the side furthest from the root, i.e., 
		the side to which other tiles can be attached.
		'''
		return self.tile.b if self.orientation == Orientation.NORMAL else self.tile.a
	
	def find_attach_position(self, tile):
		'''
		Return the leaf node under which we should add the given tile.

		This only is useful when the game is in the OPEN state.  This doesn't
		know about the rules for CHICKIE and ROOT play.

		Currently, this does a depth-first search and returns the first result.

		Raises a ValueError if the tile provided can't be attached under this tree.
		'''
		# open play - can only attach to leaves
		for node in self.leaves:
			if node.bottom in tile.ends:
				return node
		
		# if we didn't find a place to attach, then this tile must be un-attachable, 
		# and we shouldn't have been passed it in the first place
		raise ValueError('can\'t attach this tile: %s' % tile)

class Root(Node):
	'''
	Although the above Node class covers the use cases of Root, not having it means
	one must be mindful to observe certain conventions when creating the topmost
	Node in a new tree, e.g. to set its Orientation to NORMAL, and giving it the
	right branching factor.

	This class is a convenience for these conventions.
	'''
	def __init__(self, tile):
		self.children = []
		self.tile = tile
		self.max_children = 4
		self.orientation = Orientation.NORMAL

class Player(object):
	'''
	Base class for all player strategies.

	Each Player keeps track of it's name and the tiles in its hand.

	There are two methods for fetching a tile from the player's hand:
	1) pick_tile(opportunities): given a set of opportunities (all of
			which must be in the player's hand), choose one to play,
			remove it from the hand, and return it.
	2) fetch_tile(a, b): if the player has a tile with ends 'a' and 'b',
			remove it from the player's hand and return it.

	TODO: these method names are kind of weird.  Maybe this is indicative
	of bad factoring.
	'''
	def __init__(self, name):
		self.name = name
		self.hand = []

	def add_tile(self, tile):
		'''
		Add a tile into a player's hand
		'''
		self.hand.append(tile)

	def fetch_tile(self, a, b):
		'''
		If the player has a tile with ends 'a' and 'b', remove it from the 
		player's hand and return it.  Otherwise, return None.

		The order of the ends 'a' and 'b' don't matter; if 'a' and 'b' aren't
		equal, i.e. the tile requested isn't a double, then fetch_tile will 
		check for both (a, b) and (b, a).
		'''
		for tile in self.hand:
			if (tile.a == a and tile.b == b) or (tile.a == b and tile.a ==a):
				self.hand.remove(tile)
				return tile

	def pick_tile(self, opportunities):
		'''
		Call the _pick_tile method to do the actual choosing, then remove the
		chosen tile from the player's hand and return it.
		'''
		chosen = self._pick_tile(opportunities)
		self.hand.remove(chosen)
		return chosen

	def _pick_tile(self, opportunities):
		'Overriden by derived classes to implement their choosing strategies.'
		raise NotImplementedError

class Tile(object):
	'''
	A domino.  Has two ends with a number of pips on either end.

	We'll call the ends of the tile "a" and "b".  The distinction is 
	arbitrary, but one we'll use in determining Orientation
	'''
	def __init__(self, a, b):
		self.a = a
		self.b = b

	def __str__(self):
		return '<Tile (%s, %s)>' % (self.a, self.b)

	@property
	def is_double(self):
		'''
		Return True if this is a double
		'''
		return self.a == self.b

	@property
	def ends(self):
		'''
		Return an iterable of the ends of this tile
		'''
		return (self.a, self.b)

	@property
	def value(self):
		'''
		Return the scoring value of this tile, e.g. the sum of its pips, unless it's a double blank
		'''
		raw_score = self.a + self.b
		return DOUBLE_BLANK_SCORE if raw_score == 0 else raw_score

class RandomPlayer(Player):
	'''
	Plays opportunities randomly
	'''
	def _pick_tile(self, opportunities):
		'''
		Return one of 'opportunities' at random
		'opportunities' is guaranteed to not be empty
		'''
		return random.choice(opportunities)

class MaxValuePlayer(Player):
	'''
	Plays only the highest-value tiles first.
	'''
	def _pick_tile(self, opportunities):
		'''
		Return the element from 'opportunities' with the highest score value
		'opportunities' is guaranteed to not be empty
		'''
		return sorted(opportunities, key=operator.attrgetter('value'), reverse=True)[0]