import React from 'react';

// Mock framer-motion for testing
const motion = {
  div: React.forwardRef(({ children, ...props }, ref) => 
    React.createElement('div', { ...props, ref }, children)
  ),
  span: React.forwardRef(({ children, ...props }, ref) => 
    React.createElement('span', { ...props, ref }, children)
  ),
  button: React.forwardRef(({ children, ...props }, ref) => 
    React.createElement('button', { ...props, ref }, children)
  ),
  // Add more motion elements as needed
};

const AnimatePresence = ({ children }) => children;

const useAnimation = () => ({
  start: jest.fn(),
  stop: jest.fn(),
  set: jest.fn()
});

const useMotionValue = (initial) => ({
  get: jest.fn(() => initial),
  set: jest.fn(),
  subscribe: jest.fn()
});

const useTransform = () => ({
  get: jest.fn(),
  set: jest.fn(),
  subscribe: jest.fn()
});

export {
  motion,
  AnimatePresence,
  useAnimation,
  useMotionValue,
  useTransform
};