import unittest
from staghunt import *
import numpy as np


class TestStagHunt(unittest.TestCase):
    """
    Unit test class for belief propagation implementation
    """

    def test_ground_vs_pairwise(self):
        """
        Tests the correctness of the simplified pairwise model by comparing it with the ground truth model
        Asserts that the results of BP are the same in both of them, thus giving the same trajectories
        :return: None
        """
        ground_model, pairwise_model = setup_two_models(type1='torch', type2='torch')

        ground_model.build_ground_model()
        pairwise_model.build_model()

        for i in range(ground_model.horizon - 1):
            print("Ground:   ", end='')
            ground_model.infer()
            ground_model.compute_probabilities()
            ground_model.move_next(break_ties='first')
            ground_model.update_model()

            print("Pairwise: ", end='')
            pairwise_model.infer()
            pairwise_model.compute_probabilities()
            pairwise_model.move_next(break_ties='first')
            pairwise_model.update_model()

            # compare marginals
            assert compare_beliefs(ground_model.bp.var_probabilities, pairwise_model.bp.var_probabilities)
            # compare computed conditional probabilities used to decide next step
            for key in ground_model.bp.conditional_probabilities:
                if not (key == (new_var('x', ground_model.horizon, 1), new_var('x', ground_model.horizon, 2))
                        or key == (new_var('x', ground_model.horizon, 2), new_var('x', ground_model.horizon, 1))):
                    c = ground_model.bp.conditional_probabilities[key]
                    d = pairwise_model.bp.conditional_probabilities[key]
                    assert np.allclose(c, d, equal_nan=True)

    def test_matrix_vs_torch(self):
        """
        Tests the consistence between python and torch matrix BP
        :return:
        """
        matrix_model, torch_model = setup_two_models(type1='python', type2='torch')

        matrix_model.MIN = -float('inf')
        matrix_model.build_model()
        torch_model.build_model()

        assert np.all(torch_model.mrf.unary_mat.numpy() == matrix_model.mrf.unary_mat), \
            "unary matrices are not equal"
        assert np.all(torch_model.mrf.edge_pot_tensor.numpy() == matrix_model.mrf.edge_pot_tensor), \
            "edge tensors are not equal"

        for i in range(matrix_model.horizon - 1):
            print("Matrix: ", end='')
            matrix_model.infer(inference_type='matrix')
            matrix_model.compute_probabilities()
            matrix_model.move_next(break_ties='first')
            matrix_model.update_model()

            print("Torch:  ", end='')
            torch_model.infer()
            torch_model.compute_probabilities()
            torch_model.move_next(break_ties='first')
            torch_model.update_model()

            assert matrix_model.aPos == torch_model.aPos, "Trajectories differ"

            # compare marginals
            assert compare_beliefs(matrix_model.bp.var_probabilities, torch_model.bp.var_probabilities), \
                "Marginal probabilities differ"
            # compare conditional probabilities
            assert compare_beliefs(matrix_model.bp.conditional_probabilities,
                                   torch_model.bp.conditional_probabilities), \
                "Conditional probabilities differ"


def setup_two_models(num_agents=2, type1='python', type2='python'):
    """
    Utility to set up two different instances of StagHuntMRF with the exact same random configuration
    :param num_agents: Number of agents
    :param type1: Type of the first model: python or torch
    :param type2: Type of the second model: python or torch
    :return: Two StagHuntMRF instances
    """
    if type1 == 'python':
        model_1 = MatrixStagHuntModel()
    else:
        model_1 = TorchStagHuntModel()

    if type2 == 'python':
        model_2 = MatrixStagHuntModel()
    else:
        model_2 = TorchStagHuntModel()

    # random.seed(1)
    lmb = random.uniform(0.1, 10)
    r_h = random.randint(-5, -1)
    r_s = random.randint(-10, -5)
    horizon = random.randint(4, 15)
    size = random.randint(5, 10)

    model_1.lmb = lmb
    model_1.r_h = r_h
    model_1.r_s = r_s
    model_1.horizon = horizon
    model_1.new_game_sample(size=(size, size), num_agents=num_agents)

    model_2.lmb = lmb
    model_2.r_h = r_h
    model_2.r_s = r_s
    model_2.horizon = horizon
    model_2.size = (size, size)
    model_2.set_game_config(game_conf=model_1.get_game_config())

    return model_1, model_2


def compare_beliefs(belief_dict_1, belief_dict_2):
    """
    Utility to compare two belief or probability dictionaries.
    :param belief_dict_1:
    :param belief_dict_2:
    :return: Boolean - True if beliefs coincide for every variable, false otherwise
    """
    check = []
    for key in belief_dict_1:
        if key[0] == 'x':
            a = belief_dict_1[key]
            if not isinstance(a, np.ndarray):
                a = a.numpy()
            b = belief_dict_2[key]
            if not isinstance(b, np.ndarray):
                b = b.numpy()
            check.append(np.allclose(a, b, equal_nan=True))
    return all(check)
