import argparse
import gym
import glob
import os

import numpy as np
import torch
import torch.nn as nn
from torch.nn import functional as F
import torch.optim as optim
from torch.autograd import Variable
import re

class Policy(nn.Module):
  def __init__(self, D=80*80, H=200):
    super(Policy, self).__init__()
    self.D = D
    self.H = H
    self.polcy_net = nn.Sequential(
      nn.Linear(D, H, bias=False),
      nn.ReLU(),
      nn.Linear(H, 1, bias=False),
      nn.Sigmoid()
    )
    self.saved_log_probs = []

  def forward(self, x):
      p = self.polcy_net(x)
      return p

  def select_action(self, x: np.array):
    x = torch.tensor(x, dtype=torch.float32, requires_grad=True)
    aprob = self.forward(x)
    action = 1 if aprob < torch.rand(1) else 0
    
    self.saved_log_probs.append(torch.log(aprob) if action == 1 else torch.log(1 - aprob))
    return action

  def clear(self):
    del self.saved_log_probs[:]
    self.saved_log_probs = []

def prepro(I):
  """ prepro 210x160x3 uint8 frame into 6400 (80x80) 1D float vector """
  I = I[35:195] # crop
  I = I[::2,::2,0] # downsample by factor of 2
  I[I == 144] = 0 # erase background (background type 1)
  I[I == 109] = 0 # erase background (background type 2)
  I[I != 0] = 1 # everything else (paddles, ball) just set to 1
  return I.astype(float).ravel()

def discount_rewards(r, gamma):
  """ take 1D float array of rewards and compute discounted reward """
  discounted_r = np.zeros_like(r)
  running_add = 0
  for t in reversed(range(0, r.size)):
    if r[t] != 0: running_add = 0 # reset the sum, since this was a game boundary (pong specific!)
    running_add = running_add * gamma + r[t]
    discounted_r[t] = running_add
  return discounted_r

def get_latest_checkpoint(checkpoint_dir):
  files = glob.glob(checkpoint_dir + '/*.pth')
  if len(files) == 0:
    return None
  else:
    return max(files, key=os.path.getctime)

def main(args):
  env = gym.make("Pong-v0") if not args.render else gym.make("Pong-v0",render_mode='human')
  observation = env.reset()
  prev_x = None # used in computing the difference frame
  xs,drs = [],[]
  running_reward = None
  reward_sum = 0
  episode_number = 0

  model = Policy(D=args.D, H=args.H)
  optimizer = optim.RMSprop(model.parameters(), lr=args.learning_rate, weight_decay=args.decay_rate)

  if args.resume:
    model_path = get_latest_checkpoint(args.save_path)
    # path = args.save_path + '/model-%d.pth' % episode_number
    model.load_state_dict(torch.load(model_path))

  while True:
    cur_x = prepro(observation)
    x = cur_x - prev_x if prev_x is not None else np.zeros(args.D)
    prev_x = cur_x
    y = model.select_action(x)

    xs.append(x)

    action = y + 2

    observation, reward, done, _ = env.step(action)
    reward_sum += reward

    drs.append(reward)

    if done:
      episode_number += 1

      epr = np.vstack(drs)
      xs, drs = [],[]

      discounted_epr = discount_rewards(epr, args.gamma)
      discounted_epr = torch.from_numpy(discounted_epr).float()
      discounted_epr = (discounted_epr - discounted_epr.mean()) / (discounted_epr.std() + np.finfo(np.float32).eps)

      loss = torch.concat(model.saved_log_probs) * discounted_epr.flatten()
      loss = -loss.sum()

      optimizer.zero_grad()
      loss.backward()
      optimizer.step()

      # if episode_number % args.print_every == 0:
      #   print('Episode %d. reward: %f. loss: %f' % (episode_number, reward_sum, loss.item()))
      
      running_reward = reward_sum if running_reward is None else running_reward * 0.99 + reward_sum * 0.01
      print('resetting env. episode reward total was %f. running mean: %f' % (reward_sum, running_reward))
      model.clear()
      reward_sum = 0
      observation = env.reset()
      prev_x = None

      if episode_number % args.save_every == 0:
        torch.save(model.state_dict(), args.save_path + '/model-%d.pth' % episode_number)

    if reward != 0: # Pong has either +1 or -1 reward exactly when game ends.
      print(('ep %d: game finished, reward: %f' % (episode_number, reward)) + ('' if reward == -1 else ' !!!!!!!!'))

if __name__ == "__main__":
  parser = argparse.ArgumentParser(description='A PyTorch implementation of PG-Pong')
  parser.add_argument('--H', type=int, default=200, help = 'number of hidden layer neurons')
  parser.add_argument('--D', type=int, default=80*80, help = 'input dimensionality: 80x80 grid')
  parser.add_argument('--render', action='store_true', help='render the environment')
  parser.add_argument('--gamma', type=float, default=0.99,
                      help='discount factor (default: 0.99)')
  parser.add_argument('--learning_rate', type=float, default=1e-4,
                      help='learning rate (default: 1e-4)')
  parser.add_argument('--decay_rate', type=float, default=0.99,
                      help='decay rate for RMSProp (default: 0.99)')
  parser.add_argument('--batch-size', type=int, default=10, help="batch size")
  parser.add_argument('--resume', action='store_true', default=False, help="resume from previous checkpoint")
  parser.add_argument('--save_path', type=str, default='checkpoints', help="path to save checkpoints")
  parser.add_argument('--save_every', type=int, default=50, help="save every n episodes")
  parser.add_argument('--print_every', type=int, default=10, help="print every n episodes")

  args = parser.parse_args()
  main(args)