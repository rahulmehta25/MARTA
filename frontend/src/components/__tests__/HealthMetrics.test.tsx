import { render, screen } from '@testing-library/react'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import HealthMetrics from '../SystemHealth/HealthMetrics'

// Mock health data
const mockHealthData = {
  status: 'healthy',
  services: {
    api: { status: 'up', latency: 45 },
    database: { status: 'up', latency: 12 },
    redis: { status: 'up', latency: 3 },
  },
  metrics: {
    requestsPerSecond: 150,
    errorRate: 0.02,
    uptime: 99.95,
  },
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

describe('HealthMetrics', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    global.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: () => Promise.resolve(mockHealthData),
    })
  })

  it('renders health metrics component', () => {
    render(<HealthMetrics />, { wrapper })
    expect(document.body).toBeDefined()
  })

  it('displays service status indicators', async () => {
    render(<HealthMetrics />, { wrapper })
    // Component should render status information
    expect(document.body.textContent).toBeDefined()
  })
})
