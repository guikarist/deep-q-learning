import random
import os
import zmq
import json
import experience_pb2
from collections import deque

import gym
import numpy as np
from tensorflow.keras.layers import Dense, Conv2D, Flatten
from tensorflow.keras.models import Sequential
from tensorflow.keras.optimizers import Adam


class DQNAgent:
    def __init__(self, state_size, action_size):
        self.state_size = state_size
        self.action_size = action_size
        self.replay_buffer = deque(maxlen=2000)
        self.gamma = 0.95  # Discount Rate
        self.epsilon = 1.0  # Exploration Rate
        self.epsilon_min = 0.01
        self.epsilon_decay = 0.995
        self.learning_rate = 0.001
        self.model = self._build_model()

    def _build_model(self):
        """Build Neural Net for Deep Q-learning Model"""

        model = Sequential()
        model.add(Dense(256, input_dim=self.state_size, activation='relu'))
        model.add(Dense(128, activation='relu'))
        model.add(Dense(64, activation='relu'))
        model.add(Dense(self.action_size, activation='linear'))
        model.compile(loss='mse', optimizer=Adam(lr=self.learning_rate))
        
        return model

    def act(self, state):
        if np.random.rand() <= self.epsilon:
            return random.randrange(self.action_size)
        act_values = self.model.predict(state)
        return np.argmax(act_values[0])  # returns action

    def load(self, name):
        self.model.load_weights(name)

    def save(self, name):
        self.model.save_weights(name)


if __name__ == '__main__':
    env = gym.make('Pong-ram-v0')
    state_size = env.observation_space.shape[0]
    action_size = env.action_space.n

    agent = DQNAgent(state_size, action_size)

    os.environ['KMP_WARNINGS'] = '0'
    os.environ["TF_CPP_MIN_LOG_LEVEL"]='1'
    socket = zmq.Context().socket(zmq.DEALER)
    socket.connect("tcp://172.20.0.2:6080")

    model_path = "./model_weights"
    if os.path.exists(model_path):
        os.system("rm -rf " + model_path)
    os.mkdir(model_path)

    done = False
    batch_size = 32
    num_episodes = 100000
    cnt = 0
    for e in range(num_episodes):
        state = env.reset()
        state = np.reshape(state, [1, state_size])
        for _ in range(random.randint(1, 30)):
            state, _, _, _ = env.step(0)
            state = np.reshape(state, [1, state_size])
        print("actor -- current episode {}".format(e))
        for time in range(100000):
            action = agent.act(state)
            next_state, reward, done, _ = env.step(action)
            # reward = reward if not done else -10
            next_state = np.reshape(next_state, [1, state_size])
            state = next_state

            exper = experience_pb2.Exper()
            exper.now_state.pos.extend(state.tolist()[0])
            exper.action = action
            exper.reward = reward
            exper.next_state.pos.extend(next_state.tolist()[0])
            exper.done = done

            socket.send(exper.SerializeToString())
            cnt += 1

            if done:
                break
            if cnt > batch_size:
                # weights = socket.recv()
                # with open(model_path + "/syf-eposide_{}-time_{}.h5".format(e, time),"wb") as file:
                #     file.write(weights)
                # agent.load(model_path + "/syf-eposide_{}-time_{}.h5".format(e, time))
                if agent.epsilon > agent.epsilon_min:
                    agent.epsilon *= agent.epsilon_decay
        
        if e % 3 == 0:
            weights = socket.recv()
            with open(model_path + "/syf-eposide_{}-time_{}.h5".format(e, time),"wb") as file:
                file.write(weights)
            agent.load(model_path + "/syf-eposide_{}-time_{}.h5".format(e, time))
            print("actor -- updata model")
