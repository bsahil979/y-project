import { useContext } from 'react';
import { PortfolioContext } from '../contexts/PortfolioContext.js';

export default function usePortfolioSnapshot() {
  const state = useContext(PortfolioContext);
  if (!state) throw new Error('Portfolio views require the shared PortfolioContext.');
  return state;
}
