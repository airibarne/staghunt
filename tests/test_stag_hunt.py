"""Test class to test stag hunt game implementation"""
import random
import unittest
import numpy as np
from staghunt import StagHuntModel, MatrixStagHuntModel, new_var


class TestStagHunt(unittest.TestCase):
    """
    Unit test class for belief propagation implementation
    """

    def test_phi_q_factor(self):
        """
        Correctness of the phi_q factor efficient computation by comparing it with the explicit way of computing it
        :return: None
        """
        sh_model = StagHuntModel()
        mx_model = MatrixStagHuntModel()
        size = (random.randint(5, 20), random.randint(5, 20))
        sh_model.size = size
        mx_model.size = size

        sh_phi_q = sh_model.build_phi_q()
        mx_phi_q = mx_model.build_phi_q()

        assert np.equal(np.array(sh_phi_q), mx_phi_q).all()

    def test_ground_vs_pairwise(self):
        """
        Correctness of the simplified pairwise model vs the ground truth model
        :return: None
        """
        ground_model, pairwise_model = setup_two_models(num_agents=2)

        ground_model.build_ground_model()
        pairwise_model.build_model()

        for i in range(ground_model.horizon-1):
            ground_model.infer(inference_type='slow')
            ground_model.compute_probabilities()
            ground_model.move_next(break_ties='first')
            ground_model.update_model()

            pairwise_model.infer(inference_type='slow')
            pairwise_model.compute_probabilities()
            pairwise_model.move_next(break_ties='first')
            pairwise_model.update_model()

            # compare marginals
            assert compare_beliefs(ground_model.bp.var_probabilities, pairwise_model.bp.var_probabilities)

            # compare computed conditional probabilities used to decide next step
            for key in ground_model.bp.conditional_probabilities:
                if not(key == (new_var('x', ground_model.horizon, 1), new_var('x', ground_model.horizon, 2))
                        or key == (new_var('x', ground_model.horizon, 2), new_var('x', ground_model.horizon, 1))):
                    c = ground_model.bp.conditional_probabilities[key]
                    d = pairwise_model.bp.conditional_probabilities[key]
                    assert np.allclose(c, d, equal_nan=True)

    def test_slow_vs_matrix(self):
        """
        Consistency of matrix BP versus slow BP
        :return:
        """
        slow_model, matrix_model = setup_two_models()

        slow_model.build_model()
        matrix_model.build_model()

        for i in range(slow_model.horizon - 1):
            slow_model.infer(inference_type='slow')
            slow_model.compute_probabilities()
            slow_model.move_next(break_ties='first')
            slow_model.update_model()

            matrix_model.infer(inference_type='matrix')
            matrix_model.compute_probabilities()
            matrix_model.move_next(break_ties='first')
            matrix_model.update_model()

            # compare marginals
            assert compare_beliefs(slow_model.bp.var_probabilities, matrix_model.bp.var_probabilities)

            # compare conditional probabilities
            assert compare_beliefs(slow_model.bp.conditional_probabilities, matrix_model.bp.conditional_probabilities)

    def test_clamp_vs_advance(self):
        """
        Is it the same to advance by clamping states than by shortening the model clamping only the first state?
        :return:
        """
        clamp_model, advance_model = setup_two_models()

        clamp_model.build_model()
        advance_model.build_model()

        clamp_trajectories = []
        advance_trajectories = []
        for i in range(clamp_model.horizon-1):
            clamp_trajectories.append(clamp_model.aPos.copy())
            clamp_model.infer(inference_type='slow')
            clamp_model.compute_probabilities()
            clamp_model.move_next(break_ties='first')
            clamp_model.update_model()

            advance_trajectories.append(advance_model.aPos.copy())
            advance_model.infer(inference_type='slow')
            advance_model.compute_probabilities()
            advance_model.move_next(break_ties='first')
            advance_model.time = 1
            advance_model.horizon -= 1
            advance_model.build_model()

        clamp_trajectories.append(clamp_model.aPos.copy())
        advance_trajectories.append(advance_model.aPos.copy())

        assert np.all(advance_trajectories == clamp_trajectories)

    def test_fast_build_tensors(self):
        """
        The fast-built unary matrix coincides with the one built from the potentials by the mrftools object
        :return:
        """
        fast_model, slow_model = setup_two_models()
        fast_model.fast_build_model()
        slow_model.build_model()

        for var, index_slow in slow_model.mrf.var_index.items():
            index_fast = fast_model.mrf.var_index[var]
            assert np.equal(slow_model.mrf.unary_mat[:, index_slow], fast_model.mrf.unary_mat[:, index_fast]).all()

        fast_model, slow_model = setup_two_models()
        fast_model.fast_build_model()
        slow_model.build_model()
        assert len(fast_model.mrf.message_index) == len(slow_model.mrf.message_index)
        for var, index_slow in slow_model.mrf.message_index.items():
            if var in fast_model.mrf.message_index.keys():
                index_fast = fast_model.mrf.message_index[var]
                assert np.equal(slow_model.mrf.edge_pot_tensor[:, :, index_slow],
                                fast_model.mrf.edge_pot_tensor[:, :, index_fast]).all()
            else:
                index_fast = fast_model.mrf.message_index[var[::-1]]
                assert np.equal(slow_model.mrf.edge_pot_tensor[:, :, index_slow].T,
                                fast_model.mrf.edge_pot_tensor[:, :, index_fast]).all()


def setup_two_models(num_agents=None):
    """
    Utility to set up two different instances of StagHuntMRF with the exact same random configuration
    :param num_agents: Number of agents
    :return: Two StagHuntMRF instances
    """
    model_1 = MatrixStagHuntModel()
    model_2 = MatrixStagHuntModel()

    # random.seed(1)
    lmb = random.uniform(0.1, 10)
    r_h = random.randint(-5, -1)
    r_s = random.randint(-10, -5)
    horizon = random.randint(4, 15)
    size = random.randint(5, 15)

    if not num_agents:
        num_agents = random.randint(2, size // 2)

    model_1.lmb = lmb
    model_1.r_h = r_h
    model_1.r_s = r_s
    model_1.horizon = horizon
    model_1.new_game_sample(size=(size, size), num_agents=num_agents)

    model_2.lmb = lmb
    model_2.r_h = r_h
    model_2.r_s = r_s
    model_2.horizon = horizon
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
        a = belief_dict_1[key]
        b = belief_dict_2[key]
        check.append(np.allclose(a, b, equal_nan=True))
    return check
