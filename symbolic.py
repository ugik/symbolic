'''
Copyright (C) 2017 G.Kassabgi <https://github.com/ugik>
    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.
    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.
    You should have received a copy of the GNU General Public License
    along with this program.  If not, see <http://www.gnu.org/licenses/>.
'''

import urllib.request, json 
import copy
import time

# convenience functions

# find unique non-contiguous subsets of a list
def subSegment(patterns, span, positions, segments, loop=0, level=0):
    if level < span:
        for loop in range(level, len(patterns)):
            # a stack of positions
            positions.append(loop)
            # recursive call
            segments = subSegment(patterns, span, positions, segments, loop+1, level+1)
    else:
        segment = [p for p in positions]
        # if no duplicates in the segment
        if len(list(set(segment))) == len(segment):
            #if not duplicate:    # ignore duplicates
            if segment not in segments:
                segments.append(segment)

    if positions:
        positions.pop()

    return segments

# determine if a subset is first of its kind in the subsets list
def subset_first(subset, subsets):
    # make a copy as clear_offset() alters the object
    subset_clear = copy.deepcopy(subset)
    subset_clear.clear_offset()
    first = True
    for i,s in enumerate(subsets):
        s_clear = copy.deepcopy(s)
        s_clear = s_clear.clear_offset()
        if str(s_clear) == str(subset_clear):
            if subsets[i].get_offset('',0) < subset.get_offset('',0):
                first = False
                break
  
    return first

# find intersection between 2 masks
def mask_intersection(mask1, mask2, debug=False):
    mask = []
    # loop through subsets in outer mask
    for outer_position, outer_mask in enumerate(mask1):
        # loop through subsets in inner mask
        for inner_position, inner_mask in enumerate(mask2):
            if debug: print ('>compare', outer_mask, inner_mask)
            if str(outer_mask) == str(inner_mask):
                mask.append(outer_mask)
            elif len(outer_mask) == len(inner_mask):
                # if subsets are equal length then see if they match in the abstract
                if outer_mask.mask(inner_mask, offsets=False, debug=False):
                    if debug: print ('>mask', outer_mask.mask(inner_mask, offsets=False, debug=False))
                    mask.append(outer_mask.mask(inner_mask, offsets=False))

    if debug:
        print ()
        print ('mask list')
        for i,m in enumerate(mask):
            print (i, m)
            
    # normalize lists
    refactored_mask = []
    for i,m in enumerate(mask):
            
        if type(m) == list:
            for m_item in m:          
                refactored_mask.append(m_item)
        elif type(m) == Symbolic:
            refactored_mask.append(m)

    if debug:
        print ()
        print ('mask refactored intersection')
        for i,m in enumerate(refactored_mask):
            print (i, m)
            
    # remove dups
    dedup_mask = []
    for m in refactored_mask:
        if str(m) not in str(dedup_mask):
            dedup_mask.append(m)

    return dedup_mask

# return the largest mask
def top_mask(masks):
    masks_len = [(len(m),m) for m in masks]
    max = 0
    max_mask = None
    for l,m in masks_len:
        if l > max: 
            max = l
            max_mask = m

    return max_mask 



# symbolic structure: a list, each element a tuple of symbol (str) and a symbolic structure: [('a', [('foo', None)]
#
class Symbolic:

    # representation of placeholder symbol
    WILDCARD = '*'
    OFFSET = '_'
    
    def __init__(self, symbols=None):
        if type(symbols) == list:
            self.symbols = symbols
        elif type(symbols) == str:
            self.symbols = symbols.split(' ')
        elif type(symbols) == tuple:
            self.symbols = [symbols]
        else:
            self.symbols = None
        
        if self.symbols:
            # transform into list of tuples
            for i in range(0, len(self.symbols)):
                s = self.symbols[i]
                # handle list
                if type(s) == list:
                    self.symbols[i] = Symbolic(s)
                # if symbol is not already a symbolic structure
                elif type(s) != Symbolic and type(s) != tuple:
                    self.symbols[i] = (s, None)


    # produce all unique subsets for a list and their relative offset position
    def subsets(self, offsets=True):
        if offsets:
            self.add_offset()
            
        # list of subsets
        subsets = []
        for i, s in enumerate(self.symbols):
            for ii in range(1, len(self.symbols)+1):
                if ii >i:
                    subset = Symbolic(self.symbols[i:ii])
                    # each subset is a Symbolic structure
                    if not subset.get_symbol(self.OFFSET, partial=True):
                        subsets.append(subset)
            
        # subsets is a list of subsets and their offsets
        return subsets

    # add offset to symbol structure using OFFSET prefix
    def add_offset(self):
        for i, s in enumerate(self.symbols):
            if (not s[1] or not s[1].get_symbol(self.OFFSET, partial=True)) and self.OFFSET not in s[0]:
                # add offset symbol
                self.add_symbolic('', self.OFFSET +str(i), position=i)
            
        return self

    # clear offset in symbol structure
    def clear_offset(self):
        for i, s in enumerate(self.symbols):
            if s[1] and s[1].get_symbol(self.OFFSET, partial=True):
                # delete offset symbol
                s[1].del_symbol(self.OFFSET, partial=True)
            
        return self

    # get symbol offset
    def get_offset(self, element, position=-1, partial=False):
        s = self.get_symbol(element, position=position, partial=partial)
        if s and s[1]:
            o = s[1].get_symbol(self.OFFSET, partial=True)
            if o:
                split = o[0].split(self.OFFSET)
                if len(split) >1 and split[1].isdigit():
                    return split[1]

        
    # add symbol to structure
    def add_symbol(self, symbol):
        if self.symbols:
            self.symbols.append((symbol, None))
        elif symbol:
            self.symbols = [(symbol, None)]
        else:
            self.symbols = []

    # add symbolic structure to a symbol
    def add_symbolic(self, element, symbol, position=-1):
        if element in [e[0] for e in self.symbols] or position>-1:
            for n,s in enumerate(self.symbols):
                if s[0] == element and (n == position or position<0) or (n == position and position>-1):
                    # handle case where symbol cantains no symbolic structure
                    if not s[1]:
                        self.symbols[n] = (self.symbols[n][0], Symbolic(symbol))
                    else:
                        self.symbols[n][1].add_symbol(symbol)
        
    # delete a symbol, by element name or [optional] by list position, [optional] partial name
    def del_symbol(self, element, position=-1, partial=False):
            
        if element in [e[0] for e in self.symbols] or position>-1 or partial:
            for n, (s, sub) in enumerate(self.symbols):
                if not partial and element == s and                    (n == position or position<0) or (n == position and position>-1):
                    del self.symbols[n]
                elif partial and element in s and                    (n == position or position<0) or (n == position and position>-1):
                    del self.symbols[n]

    # get a symbol, by element name or [optional] by list position, [optional] partial name
    def get_symbol(self, element, position=-1, partial=False):

        if element in [e[0] for e in self.symbols] or position>-1 or partial:
            for n, (s, sub) in enumerate(self.symbols):
                if not partial and element == s and                    (n == position or position<0) or (n == position and position>-1):
                    return (s, sub)
                elif partial and element in s and                    (n == position or position<0) or (n == position and position>-1):
                    return (s, sub)

    # set a symbol, by element name or [optional] by list position, [optional] partial name
    def set_symbol(self, element, new, position=-1, partial=False):

        if element in [e[0] for e in self.symbols] or position>-1 or partial:
            for n, (s, sub) in enumerate(self.symbols):
                if not partial and element == s and                    (n == position or position<0) or (n == position and position>-1):
                    self.symbols[n] = (new, sub)
                elif partial and element in s and                    (n == position or position<0) or (n == position and position>-1):
                    self.symbols[n] = (new, sub)

    # get symbolic structure by symbol name or [optional] by list position
    def get_symbolic(self, element=None, symbol=None, position=-1):
        if position >= 0 and position <len(self.symbols):
                element = self.symbols[position][0]
            
        if element in [e[0] for e in self.symbols]:
            for n,s in enumerate(self.symbols):
                if s[0] == element:
                    # return the symbolic structure for this symbol
                    return self.symbols[n][1]
                    
    # list of elements
    def list_elements(self):
        if self.symbols:
            return [s for s in self.symbols]
        else:
            return []
        
    # similarity score with another symbolic structure
    def similarity(self, symbolic):
        mask = self.mask(symbolic)
        score = 0
        for m in mask:
            # longer overlapping subsets score higher
            score += len(m[0])
            
        return score        
    
    # build similarity mask between 2 symbolic structures
    # the similarity mask is a list of Symbolic structures
    def mask(self, symbolic, offsets=True, debug=False):    
        mask = []
        # copy parameter subsets so we can manipulate the list while searching
        symbolic_subsets = symbolic.subsets(offsets=offsets)
        
        # loop through our subsets
        for outer_position, outer_subset in enumerate(self.subsets(offsets=offsets)):
            for inner_position, inner_subset in enumerate(symbolic_subsets):

                if debug: 
                    print ('0:', outer_position, outer_subset, inner_position, inner_subset)
                
                match = True
                match_mask = outer_subset
                
                # note if this is the first subset of its kind in the subset list, to avoid dups
                first_subset = False if offsets and not subset_first(outer_subset, self.subsets()) else True

                # compare the str of each subset's Symbolic structure to test exact match
                if str(outer_subset) != str(inner_subset):           
                    
                    # if not same length then no match
                    if len(outer_subset) != len(inner_subset):
                        match = False

                    else:
                        # if unequal symbols are same length
                        # the mask we construct is a symbolic structure
                        match_mask = Symbolic()
                        
                        # loop through each symbol
                        for i in range(0, len(outer_subset)):
                            # gather the inner, outer symbols to look through
                            outer_symbol = outer_subset.get_symbol('', i)
                            inner_symbol = inner_subset.get_symbol('', i)

                            # correct for (symbol, None) 
                            if type(outer_symbol[0]) == tuple:
                                outer_symbol = outer_subset.get_symbol('', i)[0]
                            if type(inner_symbol[0]) == tuple:
                                inner_symbol = inner_subset.get_symbol('', i)[0]

                            if debug: print ('compare:', outer_symbol[0], inner_symbol[0])

                            # determine if position is same
                            positional = outer_subset.get_offset(outer_symbol[0], position=i) and                                 outer_subset.get_offset(outer_symbol[0], position=i) ==                                 inner_subset.get_offset(inner_symbol[0], position=i)

                            # assume symbols aren't equal
                            symbols_equal = False
                            # for symbol check for equality, ignore wildcards
                            if str(outer_symbol[0]) == str(inner_symbol[0]) and                                outer_symbol[0] != self.WILDCARD and inner_symbol[0] != self.WILDCARD:
                                
                                # symbols match
                                symbols_equal = True
                                # add only if this is the first of this symbol in the pattern or this is positional match
                                if first_subset or positional:
                                    match_mask.add_symbol(outer_symbol[0])
                                    if debug: print ('2:', match_mask.symbols)
                
                            # are symbols unequal and their respective symbolic structures empty?
                            if not symbols_equal and (not outer_symbol[1] or not inner_symbol[1]):
                                match = False; break

                            # recursive call mask() to check for abstract match of each symbol in structure
                            if not outer_symbol[1] or not inner_symbol[1]:
                                symbolics_mask = None
                            else:
                                symbolics_mask = outer_symbol[1].mask(inner_symbol[1], offsets=offsets)

                            if debug: print ('compare::', outer_symbol[1], inner_symbol[1], '>', outer_symbol[1].mask(inner_symbol[1]))

                            # are symbols unqequal and their symbolic structures return any matches?
                            if not symbols_equal and not symbolics_mask:
                                match = False; break

                            # use mask if there's a match
                            if match:
                                if debug: print ('match', match_mask)

                                # symbols match
                                # add only if this is the first of this symbol in the pattern or this is positional match
                                if first_subset or positional:
                                    if not symbols_equal or outer_symbol[0] == self.WILDCARD or inner_symbol[0] == self.WILDCARD:
                                        match_mask.add_symbol(self.WILDCARD)

                                    # add symbolics from the match subset list
                                    if symbolics_mask:
                                        for symbolics_subset in symbolics_mask:
                                            symbolics_subset.clear_offset()     
                                            # single length masks are the individual matching symbols
                                            if len(symbolics_subset) == 1:
                                                # handle (symbol, None)
                                                add_symbol = symbolics_subset.get_symbol('', 0)
                                                if type(add_symbol) == tuple:
                                                    add_symbol = symbolics_subset.get_symbol('', 0)[0]
                                                    
                                                if symbols_equal:
                                                    match_mask.add_symbolic('', add_symbol, position=i)
                                                else:
                                                    match_mask.add_symbolic('', add_symbol, position=i)
                                    
                                    # add offset if offset match
                                    if positional:
                                        if outer_subset.get_offset(outer_symbol[0], position=i):
                                            if symbols_equal:
                                                match_mask.add_symbolic(outer_symbol[0], self.OFFSET +outer_subset.get_offset(outer_symbol[0], position=i), position=i) 
                                            else:
                                                match_mask.add_symbolic(self.WILDCARD, self.OFFSET +outer_subset.get_offset(outer_symbol[0], position=i), position=i)
                                        
                                    if debug: print ('1:', match_mask)


                if match and match_mask:
                    if debug: print ('mask:', match_mask.symbols)
                    mask.append(match_mask)

        return mask

    # clean representation
    def clean(self):
        r_value = []
        for s, sub in self.symbols:
            # each symbol is either a str or tuple
            if type(s) == str:
                if sub:
                    r_value.append((s, sub))
                else:
                    r_value.append(s)
            elif type(s) == tuple:
                if s[1]:
                    r_value.append(s)
                else:
                    r_value.append(s[0])                

        return "%s" % (r_value)
    
    # class representation
    def __repr__(self):
        if self.symbols:
            return "%s" % (self.clean())
        else: 
            return 'None'

    # print() representation
    def __str__(self):
        if self.symbols:
            return "%s" % (self.clean())
        else: 
            return 'None'

    # iterator
    def __iter__(self):
        return iter(self.symbols)

    def __getitem__(self, item):
         return self.symbols[item]
        
    # len() overload function
    def __len__(self):
        return len(self.list_elements())

    # override the default Equals behavior
    def __eq__(self, other):
        if isinstance(other, self.__class__):
            return self.similarity(other) == self.similarity(self)
        return NotImplemented

    # define a non-equality test
    def __ne__(self, other):
        if isinstance(other, self.__class__):
            return not self.__eq__(other)
        return NotImplemented
    
    # hash function
    def __hash__(self):
        # use the hashcode of str(symbols)
        return hash(str(self.symbols))

    def __copy__(self):
        copy = Symbolic()
        copy.symbols = copy.deepcopy(self.symbols)
        return copy



# Reason: using patterns for reasoning
class Reason:

    # representation of placeholder symbol
    WILDCARD = '*'
    OFFSET = '_'

    # deal with basic relations and their antithesis
    relations = [{'relation': 'is', 'anti': 'is not'}, 
                 {'relation': 'is not', 'anti': 'is'}]
    
    # distinguishing features dictionary of lists
    distinguishing_features = {}
    
    def __init__(self):
        # keep pattern information in a dictionary
        self.patterns = {}

    # add a pattern to our information collection
    def add_pattern(self, pattern, attribute, relation="is", elapse=False):
        start = time.clock()
        
        # generate unique key
        key = str(len(self.patterns))
        pattern.add_offset()
        self.patterns[key] = {'pattern': pattern, 'attr': attribute, 'rela': relation}
    
        # set distinguishing features for this class
        if attribute not in self.distinguishing_features:
            self.distinguishing_features[attribute] = {}
        self.distinguishing_features[attribute][relation] = self.distinguishing(attribute, relation)

        # set distinguishing features for this class' anti-relation
        ar = None
        for r in self.relations:
            # find the anti-relation
            if r['relation'] == relation:
                ar = r['anti']
                self.distinguishing_features[attribute][ar] = self.distinguishing(attribute, ar)

        if elapse: print (time.clock() - start, 'secs')
        return

    def get_key(self, key):
        if key in self.patterns:
            return self.patterns[key]
        
    # get info for a pattern
    def get_pattern(self, pattern, debug=False):
        if debug: print('pattern', pattern)
        results = []
        for p in self.patterns:
            if debug: print (p, str(self.patterns[p]['pattern']))
            if 'pattern' in self.patterns[p] and str(self.patterns[p]['pattern']) == str(pattern):
                results.append(p)
        return results
        
    # get patterns for an attribute relation
    def get_attr(self, attribute, relation="is"):
        results = []
        for p in self.patterns:
            if 'attr' in self.patterns[p] and self.patterns[p]['attr'] == attribute and                'rela' in self.patterns[p] and self.patterns[p]['rela'] == relation:
                results.append(p)
        return results

    # return patterns attributed to an attribute
    def get_patterns(self, attribute, relation="is", debug=False):
        symbolics = []
        # list patterns that have attribute
        attr_list = self.get_attr(attribute, relation)
        # loop through patterns
        for p in attr_list:
            info = self.get_key(p)
            symbolics.append(info['pattern'])

        return {'attribute': attribute, 'relation': relation, 'patterns' : symbolics}
            
    # reason on the distinguishing features for an attribute as an OR tuple
    def distinguishingOR(self, attribute, debug=False):
        seg1, seg2 = self.sub_groups(attribute, elapse=True, debug=False)
        if debug:
            for i,p in enumerate(self.get_patterns(attribute)['patterns']):
                print (i,p)
                
        if debug:
            print (seg1, '->', self.distinguishing(attribute, include=seg1))
            print (seg2, '->', self.distinguishing(attribute, include=seg2))
            
        return self.distinguishing(attribute, include=seg1), self.distinguishing(attribute, include=seg2)
    
    # reason on the distinguishing features for an attribute
    # include is optional array of list elements to include (a subgroup)
    def distinguishing(self, attribute, relation="is", include=[], elapse=False, debug=False):
        start = time.clock()
        symbolics = []
        # list patterns that have attribute
        attr_list = self.get_attr(attribute, relation)
        # loop through patterns
        for i,p in enumerate(attr_list):
            # deal with include list (if provided)
            if include and i not in include:
                continue
                
            info = self.get_key(p)
            # make list of patterns
            symbolics.append(info['pattern'])

        if debug: print (len(symbolics), 'patterns')
        mask = []
        # capture mask of each symbolic structure and the next
        for i,s in enumerate(symbolics[:-1]):
            mask.append(s.mask(symbolics[i+1]))
            
        while len(mask) > 1:
            if debug: 
                print ('reduced to', len(mask), 'masks')
                for m in mask:
                    print (m)
                
            intersection = []
            for i,m in enumerate(mask[:-1]):
                if debug: print ('mask intersection', i, i+1)
                intersection.append(mask_intersection(m, mask[i+1], debug=debug))
            
            mask = intersection

        if elapse: print (time.clock() - start, 'secs')
        if mask:
            return mask[0]
        else:
            return None

    
    # determine if a pattern is associated with an attribute
    # steps: 1. check for equality with patterns (or anti-patterns)
    #        2. attribute distinguishing symbols (the intersection of the attribute patterns' powerset)
    #        3. relative similarity (the avg similarity score across the attribute patterns and anti-patterns)
    #
    # returns boolean and reason for it
    def determine(self, pattern, attribute, relation="is", elapse=False, debug=False):
        start = time.clock()
          
        # make sure pattern has offsets
        pattern.add_offset()
        
        # establish the anti-relation (eg. 'is' != 'is not')
        ar = None
        for r in self.relations:
            # find the anti-relation
            if r['relation'] == relation:
                ar = r['anti']
                if debug: print ('anti-relation:', ar)
                    
        # check to see if pattern matches one of the attribute patterns
        matching_keys = self.get_pattern(pattern)
        if matching_keys:
            for key in matching_keys:
                match = self.get_key(key)
                if debug: print ('key', match)
                # is there a match in an attribute pattern?
                if 'attr' in match and 'rela' in match and match['attr'] == attribute and match['rela'] == relation:
                    if debug: print('match', match)
                    if elapse: print (time.clock() - start, 'secs')
                    return True, 'exact match with attribute patterns'
                # is there a match in an attribute anti-pattern?
                if 'attr' in match and 'rela' in match and match['attr'] == attribute and match['rela'] == ar:
                    if debug: print('anti-match', match)
                    if elapse: print (time.clock() - start, 'secs')
                    return False, 'exact match with attribute anti-patterns'
        elif debug: print ('no matching patterns')

        # get the distinguishing symbols for the attribute (the intersection of its powerset) in the relation
        dis_features = self.distinguishing_features[attribute][relation]
        if debug: print ('dis', dis_features[0])
            
        match = False
    
        if dis_features:
            for feature in dis_features:
                # mark the feature with the pattern
                feature_copy = copy.deepcopy(feature)
                mask = feature_copy.mask(pattern, offsets=False)
                if debug: 
                    print ('feature', feature)
                    print ('mask', mask)
                    
                # confirm that every feature is in the mask
                match = False
                # check that one of the masks is found in the mask
                if mask:
                    for m in mask:
                        if str(m) == str(feature):
                            match = True
                            if debug: print('match', m)
                            break
                    
                    if not match:
                        if debug: print ('No Match')
                        break
                
                if debug: print ('______________________')  
                
            if match:
                if debug: print ('has distinguishing features')
                if elapse: print (time.clock() - start, 'secs')
                return True, 'has distinguishing features'

        # get the anti-relation distinguishing symbols for the attribute (the intersection of its powerset)
        if ar:
            dis_features = self.distinguishing_features[attribute][ar]
            if dis_features:
                match = False
                for feature in dis_features:
                    # mark the feature with the pattern
                    feature_copy = copy.deepcopy(feature)
                    mask = feature_copy.mask(pattern, offsets=False)
    
                    # confirm that every feature is in the mask
                    match = False
                    # check that one of the masks is found in the mask
                    if mask:
                        for m in mask:
                            if str(m) == str(feature):
                                match = True
                                break
                    
                    if not match:
                        break
        
            if match:
                if debug: print ('has distinguishing features for anti-relation')
                if elapse: print (time.clock() - start, 'secs')
                return True, 'has distinguishing features for anti-relation'

            
        # if there's no pattern match and no distinguishing features then look for relative similarity within class
        if ar:
            perfect_score = pattern.similarity(pattern)
            rela_score = anti_score = 0
            rela_count = anti_count = 0
            # get list of pattern similarity with the relation
            rela_list = self.get_attr(attribute=attribute, relation=relation)
            for rela_pattern_key in rela_list:
                rela_pattern = self.get_key(rela_pattern_key)['pattern']
                similarity = pattern.similarity(rela_pattern)
                rela_score += similarity
                rela_count += 1
                if debug: print ('+', rela_pattern, perfect_score, similarity)
   
            # get list of pattern similarity with the anti-relation
            anti_list = self.get_attr(attribute=attribute, relation=ar)
            for anti_pattern_key in anti_list:
                anti_pattern = self.get_key(anti_pattern_key)['pattern']
                anti_similarity = pattern.similarity(anti_pattern)
                anti_score += anti_similarity
                anti_count += 1
                if debug: print ('-', anti_pattern, perfect_score, anti_similarity)
            
            if rela_count == 0 or anti_count == 0: 
                if elapse: print (time.clock() - start, 'secs')
                return None, "I don't know"

            if debug: 
                print ('rela count', rela_count, 'anti count', anti_count)
                print ("rela score", float(rela_score/rela_count), "anti score", float(anti_score/anti_count))
            # determination favors the highest avg similarity score in the relation/anti-relation patterns
            if float(rela_score/rela_count) > float(anti_score/anti_count):
                if elapse: print (time.clock() - start, 'secs')
                return True, 'has higher similarity with attribute patterns than its anti-patterns'
            elif float(rela_score/rela_count) < float(anti_score/anti_count): 
                if elapse: print (time.clock() - start, 'secs')
                return False, 'has higher similarity with attribute anti-patterns than its patterns'
        
        # when all else fails None is equivalent to "I don't know"
        if elapse: print (time.clock() - start, 'secs')
        return None, "I don't know"

    # find subgroups within the attribute's patterns with the 'best' distinguishing features
    def sub_groups(self, attribute, relation='is', elapse=False, debug=False):
        start = time.clock()
        # find all non-contiguous subsets of a numerical series
        series = list(range(0, len(self.get_patterns(attribute, relation=relation)['patterns'])))
        span = int(len(series)/2)

        if len(series) < 4:
            print ('not enough patterns')
            return None, None
        
        count = 0
        for s in range(2, span+1):
            segments = subSegment(series, s, [], [])
            count += len(segments)

        patterns = self.get_patterns(attribute, relation=relation)['patterns']
        best_len = 0
        best_segment = None
        for i,segment in enumerate(segments):
            if debug: print (segment)
            dis1 = self.distinguishing('foo', include=segment)
            if debug: 
                print ('dis:', dis1, 'len:', [sum(len(d) for d in dis1)])
                print ( list(set(series).difference(segment)))
            dis2 = self.distinguishing('foo', include=list(set(series).difference(segment)))
            if debug: 
                print ('dis:', dis2, 'len:', [sum(len(d) for d in dis2)])
                print ('____________________')
            lenSum = [sum(len(d) for d in dis1)][0] + [sum(len(d) for d in dis2)][0]
            if dis1 and dis2 and lenSum > best_len:
                best_len = lenSum
                best_segment = i
        
        if debug: print ('best segment:', segments[best_segment], self.distinguishing('foo', include=segments[best_segment]))
        if debug: print ('     segment:', list(set(series).difference(segments[best_segment])), self.distinguishing('foo', include=list(set(series).difference(segments[best_segment]))))
        if elapse: print (time.clock() - start, 'secs')

        return segments[best_segment], list(set(series).difference(segments[best_segment]))


