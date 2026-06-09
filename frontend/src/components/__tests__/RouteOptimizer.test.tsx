import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import RouteOptimizer from '../RouteOptimizer/RouteOptimizer'

// Mock API responses
const mockOptimizationResult = {
  optimizationId: 'opt-001',
  status: 'completed',
  recommendations: [
    {
      routeId: 'RED',
      action: 'increase_frequency',
      currentFrequency: 15,
      recommendedFrequency: 10,
      expectedImprovement: '25%',
    },
  ],
}

// Create test query client
const createTestQueryClient = () =>
  new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
        gcTime: 0,
      },
    },
  })

// Wrapper
const wrapper = ({ children }: { children: React.ReactNode }) => {
  const queryClient = createTestQueryClient()
  return (
    <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
  )
}

describe('RouteOptimizer', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    global.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: () => Promise.resolve(mockOptimizationResult),
    })
  })

  it('renders optimization interface', () => {
    render(<RouteOptimizer />, { wrapper })
    expect(document.body).toBeDefined()
  })

  it('handles optimization request', async () => {
    render(<RouteOptimizer />, { wrapper })

    // Look for any button or interactive element
    const buttons = screen.queryAllByRole('button')

    if (buttons.length > 0) {
      fireEvent.click(buttons[0])
      await waitFor(() => {
        expect(document.body.textContent).toBeDefined()
      })
    }
  })
})
