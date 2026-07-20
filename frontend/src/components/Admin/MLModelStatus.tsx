// frontend/src/components/Admin/MLModelStatus.tsx

import React, { useState, useEffect } from 'react';
import { TrendingUp, Brain, BarChart3, Clock, AlertCircle, CheckCircle } from 'lucide-react';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts';

interface Model {
  id: string;
  name: string;
  type: string;
  accuracy: number;
  lastTrained: string;
  nextRetraining: string;
  predictions24h: number;
  avgLatency: number;
  status: 'active' | 'training' | 'error';
}

interface MLModelStatusProps {
  accuracy: number;
}

const MLModelStatus: React.FC<MLModelStatusProps> = ({ accuracy }) => {
  const [models, setModels] = useState<Model[]>([]);
  const [performanceData, setPerformanceData] = useState<any[]>([]);

  useEffect(() => {
    fetchModels();
    fetchPerformanceData();
  }, []);

  const fetchModels = async () => {
    // TODO: Fetch real model status from API
    const mockModels: Model[] = [
      {
        id: 'demand-forecast',
        name: 'Demand Forecaster',
        type: 'Prophet + LSTM Ensemble',
        accuracy: 0.92,
        lastTrained: new Date(Date.now() - 2 * 24 * 60 * 60 * 1000).toISOString(),
        nextRetraining: new Date(Date.now() + 5 * 24 * 60 * 60 * 1000).toISOString(),
        predictions24h: 2456,
        avgLatency: 125,
        status: 'active',
      },
      {
        id: 'overcrowding',
        name: 'Overcrowding Detector',
        type: 'Random Forest Classifier',
        accuracy: 0.88,
        lastTrained: new Date(Date.now() - 7 * 24 * 60 * 60 * 1000).toISOString(),
        nextRetraining: new Date(Date.now() + 1 * 24 * 60 * 60 * 1000).toISOString(),
        predictions24h: 1832,
        avgLatency: 45,
        status: 'active',
      },
      {
        id: 'route-optimizer',
        name: 'Route Optimizer',
        type: 'Genetic Algorithm',
        accuracy: 0.85,
        lastTrained: new Date(Date.now() - 1 * 24 * 60 * 60 * 1000).toISOString(),
        nextRetraining: new Date(Date.now() + 3 * 24 * 60 * 60 * 1000).toISOString(),
        predictions24h: 512,
        avgLatency: 320,
        status: 'active',
      },
      {
        id: 'surge-predictor',
        name: 'Surge Predictor',
        type: 'GradientBoost Regressor',
        accuracy: 0.90,
        lastTrained: new Date(Date.now() - 3 * 24 * 60 * 60 * 1000).toISOString(),
        nextRetraining: new Date(Date.now() + 2 * 24 * 60 * 60 * 1000).toISOString(),
        predictions24h: 3124,
        avgLatency: 68,
        status: 'training',
      },
    ];
    setModels(mockModels);
  };

  const fetchPerformanceData = async () => {
    // TODO: Fetch real performance data from API
    const mockData = Array.from({ length: 7 }, (_, i) => ({
      day: ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'][i],
      accuracy: 0.85 + Math.random() * 0.1,
      predictions: Math.floor(Math.random() * 2000) + 1000,
    }));
    setPerformanceData(mockData);
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'active':
        return <CheckCircle className="h-5 w-5 text-green-500" />;
      case 'training':
        return <Clock className="h-5 w-5 text-yellow-500 animate-pulse" />;
      case 'error':
        return <AlertCircle className="h-5 w-5 text-red-500" />;
      default:
        return null;
    }
  };

  const getDaysUntil = (date: string) => {
    const diff = new Date(date).getTime() - Date.now();
    const days = Math.floor(diff / (1000 * 60 * 60 * 24));
    return days > 0 ? `${days} days` : 'Overdue';
  };

  return (
    <div id="ml-model-status" className="space-y-6">
      {/* Overview Card */}
      <div id="ml-overview" className="bg-white rounded-lg shadow p-6">
        <div className="flex items-center mb-4">
          <Brain className="h-6 w-6 text-purple-500 mr-2" />
          <h3 className="text-lg font-medium text-gray-900">ML Model Performance</h3>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
          <div className="bg-purple-50 rounded-lg p-4">
            <p className="text-sm text-purple-600">Average Accuracy</p>
            <p className="text-2xl font-bold text-purple-900">
              {(models.reduce((sum, m) => sum + m.accuracy, 0) / models.length * 100).toFixed(1)}%
            </p>
          </div>
          <div className="bg-purple-50 rounded-lg p-4">
            <p className="text-sm text-purple-600">Total Predictions (24h)</p>
            <p className="text-2xl font-bold text-purple-900">
              {models.reduce((sum, m) => sum + m.predictions24h, 0).toLocaleString()}
            </p>
          </div>
          <div className="bg-purple-50 rounded-lg p-4">
            <p className="text-sm text-purple-600">Avg Latency</p>
            <p className="text-2xl font-bold text-purple-900">
              {(models.reduce((sum, m) => sum + m.avgLatency, 0) / models.length).toFixed(0)}ms
            </p>
          </div>
        </div>

        {/* Performance Chart */}
        <div className="mb-6">
          <h4 className="text-sm font-medium text-gray-700 mb-2">Weekly Performance</h4>
          <ResponsiveContainer width="100%" height={200}>
            <LineChart data={performanceData}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="day" />
              <YAxis yAxisId="left" domain={[0.8, 1]} />
              <YAxis yAxisId="right" orientation="right" />
              <Tooltip />
              <Legend />
              <Line
                yAxisId="left"
                type="monotone"
                dataKey="accuracy"
                stroke="#8b5cf6"
                name="Accuracy"
                strokeWidth={2}
              />
              <Line
                yAxisId="right"
                type="monotone"
                dataKey="predictions"
                stroke="#3b82f6"
                name="Predictions"
                strokeWidth={2}
              />
            </LineChart>
          </ResponsiveContainer>
        </div>

        {/* Model List */}
        <div className="space-y-4">
          <h4 className="text-sm font-medium text-gray-700">Active Models</h4>
          {models.map((model) => (
            <div
              key={model.id}
              id={`model-${model.id}`}
              className="border border-gray-200 rounded-lg p-4"
            >
              <div className="flex items-start justify-between">
                <div className="flex-1">
                  <div className="flex items-center">
                    {getStatusIcon(model.status)}
                    <h5 className="ml-2 text-sm font-medium text-gray-900">{model.name}</h5>
                    <span className="ml-2 px-2 py-1 text-xs font-medium bg-gray-100 text-gray-800 rounded">
                      {model.type}
                    </span>
                  </div>

                  <div className="mt-2 grid grid-cols-2 sm:grid-cols-5 gap-4 text-sm">
                    <div>
                      <span className="text-gray-500">Accuracy:</span>
                      <p className="font-medium text-gray-900">
                        {(model.accuracy * 100).toFixed(1)}%
                      </p>
                    </div>
                    <div>
                      <span className="text-gray-500">Last Trained:</span>
                      <p className="font-medium text-gray-900">
                        {new Date(model.lastTrained).toLocaleDateString()}
                      </p>
                    </div>
                    <div>
                      <span className="text-gray-500">Next Retraining:</span>
                      <p className="font-medium text-gray-900">
                        {getDaysUntil(model.nextRetraining)}
                      </p>
                    </div>
                    <div>
                      <span className="text-gray-500">Predictions (24h):</span>
                      <p className="font-medium text-gray-900">
                        {model.predictions24h.toLocaleString()}
                      </p>
                    </div>
                    <div>
                      <span className="text-gray-500">Latency:</span>
                      <p className="font-medium text-gray-900">{model.avgLatency}ms</p>
                    </div>
                  </div>

                  {model.status === 'training' && (
                    <div className="mt-2 flex items-center text-sm text-yellow-600">
                      <Clock className="h-4 w-4 mr-1 animate-pulse" />
                      Model retraining in progress...
                    </div>
                  )}
                </div>

                <div className="flex space-x-2">
                  <button className="text-sm text-blue-600 hover:text-blue-700">
                    View Details
                  </button>
                  <button className="text-sm text-purple-600 hover:text-purple-700">
                    Retrain
                  </button>
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};

export default MLModelStatus;