##
# test_config.py
# Unit tests for configuring tree transducer and grammar macros.
##


import unittest
import testperanto.examples
from testperanto.config import rewrite_gmacro_config
from testperanto.config import generate_sentences, init_grammar_macro
from testperanto.distmanager import DistributionManager
from testperanto.globals import EMPTY_STR
from testperanto.rules import TreeTransducerRule, TreeTransducerRuleMacro
from testperanto.rules import RuleMacroSet
from testperanto.transducer import TreeTransducer
from testperanto.trees import TreeNode
from testperanto.util import compound


GRAMMAR1 = {
    "distributions": [
        {"name": "nn", "type": "pyor", "strength": 500, "discount": 0.5},
        {"name": "adj", "type": "pyor", "strength": 100, "discount": 0.8},
        {"name": "adj~$y1", "type": "pyor", "strength": 5, "discount": 0.5}
    ],
    "macros": [
        {"rule": "$qstart -> $qnp~$z1", "zdists": ["nn"]},
        {
            "rule": "$qnp~$y1 -> (NP (amod $qadj) (head $qnn~$y1))",
            "alt": "$qnp~$y1 -> (NP (head $qnn~$y1) (amod $qadj))",
            "switch": 0
        },
        {"rule": "$qnn~$y1 -> (NN bottle)"},
        {"rule": "$qadj -> (ADJ blue)"}
    ]
}

GRAMMAR2 = {
    "distributions": [],
    "macros": [
        {"rule": "$qstart -> $qs"},
        {"rule": "$qs -> (S (nsubj $qsubj) (head $qvp))"},
        {
            "rule": "$qvp -> (VP (head $qvb) (dobj $qnp))",
            "alt": "$qvp -> (VP (dobj $qnp) (head $qvb))",
            "switch": 0
        },
        {
            "rule": "$qnp -> (NP (amod $qadj) (head $qobj))",
            "alt": "$qnp -> (NP (head $qobj) (amod $qadj))",
            "switch": 1
        },
        {"rule": "$qvb -> (VB chased)"},
        {"rule": "$qsubj -> (NN dogs)"},
        {"rule": "$qobj -> (NN cats)"},
        {"rule": "$qadj -> (ADJ concerned)"}
    ]
}


def leaf_string(node):
    leaves = [compound(leaf.get_label()) for leaf in node.get_leaves()]
    leaves = [leaf for leaf in leaves if leaf != EMPTY_STR]
    output = ' '.join(leaves)
    return output


class TestConfig(unittest.TestCase):

    def test_config(self):
        rule1 = {'rule': '$qtop~$y1 -> (TOP $qn~$z1)', 'zdists': ['a']}
        rule2 = {'rule': '$qn~$y1 -> (N n~$y1 $qnprop~$z1)', 'zdists': ['a']}
        rule3 = {'rule': '$qnprop~$y1 -> (NPROP def plu)'}
        rule4 = {'rule': '$qnprop~$y1 -> (NPROP def sng)'}
        config = {"distributions": [{"name": "a", "type": 'uniform', "domain": [1, 2, 3]}],
                  "macros": [rule1, rule2, rule3, rule4]}
        transducer = TreeTransducer.from_config(config)
        in_tree = TreeNode.from_str('$qtop~0')
        out_trees = set([str(transducer.run(in_tree)) for _ in range(500)])
        self.assertEqual(out_trees, {'(TOP (N n~1 (NPROP def sng)))',
                                     '(TOP (N n~1 (NPROP def plu)))',
                                     '(TOP (N n~2 (NPROP def sng)))',
                                     '(TOP (N n~2 (NPROP def plu)))',
                                     '(TOP (N n~3 (NPROP def sng)))',
                                     '(TOP (N n~3 (NPROP def plu)))'})


    def test_grammar_config(self):
        rule1 = {'rule': 'TOP -> S.$z1', 'zdists': ['vb']}
        rule2 = {'rule': 'S.$y1 -> NN.$z1 VB.$y1', 'zdists': ['nn.$y1']}
        rule3 = {'rule': 'NN.$y1 -> (@verbatim noun.$y1)'}
        rule4 = {'rule': 'VB.$y1 -> (@vb (STEM verb.$y1) (COUNT sng) (PERSON 3) (TENSE perfect))'}
        config = {"distributions": [{"name": "vb", "type": 'alternating'},
                                    {'name': 'nn', 'type': 'alternating'},
                                    {"name": "nn.$y1", "type": 'averager'}],
                  "grammar": [rule1, rule2, rule3, rule4]}
        expected = {'distributions': [{'name': 'vb', 'type': 'alternating'},
                                      {'name': 'nn', 'type': 'alternating'},
                                      {'name': 'nn~$y1', 'type': 'averager'}],
                    'macros': [{'rule': '$qtop -> (X $qs~$z1)', 'zdists': ['vb']},
                               {'rule': '$qs~$y1 -> (X $qnn~$z1 $qvb~$y1)', 'zdists': ['nn~$y1']},
                               {'rule': '$qnn~$y1 -> (X (@verbatim noun~$y1))'},
                               {'rule': '$qvb~$y1 -> (X (@vb (STEM verb~$y1) (COUNT sng) (PERSON 3) (TENSE perfect)))'}]}
        rewritten = rewrite_gmacro_config(config)
        self.assertEqual(expected, rewrite_gmacro_config(rewritten))
        transducer = TreeTransducer.from_config(rewritten)
        sents = generate_sentences(transducer, start_state='TOP', num_to_generate=5)
        self.assertEqual(sents[0].split()[0], 'noun.0')
        self.assertEqual(sents[1].split()[0], 'noun.100')
        self.assertEqual(sents[2].split()[0], 'noun.40')
        self.assertEqual(sents[3].split()[0], 'noun.60')
        self.assertEqual(sents[4].split()[0], 'noun.0')
        for i in range(5):
            self.assertEqual(sents[i].split()[1][-4:], 'ized')


    def test_grammar_config2(self):
        rule1 = {'rule': 'TOP -> S.$z1', 'zdists': ['vb']}
        rule2 = {'rule': 'S.$y1 -> NN.$z1 VB.$y1', 'zdists': ['nn.$y1']}
        rule3 = {'rule': 'NN.$y1 -> (@verbatim noun.$y1)'}
        rule4 = {'rule': 'VB.$y1 -> (@verbatim verb.$y1)'}
        config = {"distributions": [{"name": "vb", "type": 'alternating'},
                                    {'name': 'nn', 'type': 'alternating'},
                                    {"name": "nn.$y1", "type": 'averager'}],
                  "grammar": [rule1, rule2, rule3, rule4]}
        transducer = init_grammar_macro(config)
        sents = generate_sentences(transducer, start_state='TOP', num_to_generate=5)
        self.assertEqual(sents[0], "noun.0 verb.0")
        self.assertEqual(sents[1], "noun.100 verb.100")
        self.assertEqual(sents[2], "noun.40 verb.0")
        self.assertEqual(sents[3], "noun.60 verb.100")
        self.assertEqual(sents[4], "noun.0 verb.0")

    def test_switched_grammar1a(self):
        grammar = TreeTransducer.from_config(GRAMMAR1, "1")
        output = grammar.run(TreeNode.from_str("$qstart"))
        expected = "(NP (head (NN bottle)) (amod (ADJ blue)))"
        self.assertEqual(str(output), expected)

    def test_switched_grammar1b(self):
        grammar = TreeTransducer.from_config(GRAMMAR1, "0")
        output = grammar.run(TreeNode.from_str("$qstart"))
        expected = "(NP (amod (ADJ blue)) (head (NN bottle)))"
        self.assertEqual(str(output), expected)

    def test_switched_grammar2a(self):
        grammar = TreeTransducer.from_config(GRAMMAR2, "00")
        output = grammar.run(TreeNode.from_str("$qstart"))
        expected = "(S (nsubj (NN dogs)) (head (VP (head (VB chased)) (dobj (NP (amod (ADJ concerned)) (head (NN cats)))))))"
        self.assertEqual(str(output), expected)
        self.assertEqual(leaf_string(output), "dogs chased concerned cats")

    def test_switched_grammar2b(self):
        grammar = TreeTransducer.from_config(GRAMMAR2, "10")
        output = grammar.run(TreeNode.from_str("$qstart"))
        expected = "(S (nsubj (NN dogs)) (head (VP (dobj (NP (amod (ADJ concerned)) (head (NN cats)))) (head (VB chased)))))"
        self.assertEqual(str(output), expected)
        self.assertEqual(leaf_string(output), "dogs concerned cats chased")

    def test_switched_grammar2c(self):
        grammar = TreeTransducer.from_config(GRAMMAR2, "01")
        output = grammar.run(TreeNode.from_str("$qstart"))
        expected = "(S (nsubj (NN dogs)) (head (VP (head (VB chased)) (dobj (NP (head (NN cats)) (amod (ADJ concerned)))))))"
        self.assertEqual(str(output), expected)
        self.assertEqual(leaf_string(output), "dogs chased cats concerned")

    def test_switched_grammar2d(self):
        grammar = TreeTransducer.from_config(GRAMMAR2, "11")
        output = grammar.run(TreeNode.from_str("$qstart"))
        expected = "(S (nsubj (NN dogs)) (head (VP (dobj (NP (head (NN cats)) (amod (ADJ concerned)))) (head (VB chased)))))"
        self.assertEqual(str(output), expected)
        self.assertEqual(leaf_string(output), "dogs cats concerned chased")


if __name__ == "__main__":
    unittest.main()   