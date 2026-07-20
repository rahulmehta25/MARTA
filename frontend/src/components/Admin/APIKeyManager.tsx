// frontend/src/components/Admin/APIKeyManager.tsx

import React, { useState, useEffect } from 'react';
import { Key, Plus, Copy, Trash2, Eye, EyeOff, AlertCircle } from 'lucide-react';

interface APIKey {
  id: string;
  name: string;
  key: string;
  keyPreview: string;
  permissions: string[];
  rateLimit: {
    perMinute: number;
    perHour: number;
    perDay: number;
  };
  lastUsed: string | null;
  expiresAt: string | null;
  createdAt: string;
  isActive: boolean;
}

const APIKeyManager: React.FC = () => {
  const [apiKeys, setApiKeys] = useState<APIKey[]>([]);
  const [showNewKeyModal, setShowNewKeyModal] = useState(false);
  const [newKeyName, setNewKeyName] = useState('');
  const [selectedPermissions, setSelectedPermissions] = useState<string[]>([]);
  const [copiedKeyId, setCopiedKeyId] = useState<string | null>(null);

  const availablePermissions = [
    'read:routes',
    'read:stops',
    'read:metrics',
    'read:realtime',
    'write:data',
    'admin:users',
    'admin:system',
  ];

  useEffect(() => {
    fetchAPIKeys();
  }, []);

  const fetchAPIKeys = async () => {
    // TODO: Fetch real API keys from backend
    const mockKeys: APIKey[] = [
      {
        id: '1',
        name: 'Production API',
        key: 'sk_live_abcd1234efgh5678',
        keyPreview: 'sk_live_...5678',
        permissions: ['read:routes', 'read:stops', 'read:metrics'],
        rateLimit: { perMinute: 100, perHour: 2000, perDay: 20000 },
        lastUsed: new Date(Date.now() - 2 * 60 * 60 * 1000).toISOString(),
        expiresAt: null,
        createdAt: new Date(Date.now() - 30 * 24 * 60 * 60 * 1000).toISOString(),
        isActive: true,
      },
      {
        id: '2',
        name: 'Development API',
        key: 'sk_test_ijkl9012mnop3456',
        keyPreview: 'sk_test_...3456',
        permissions: ['read:routes', 'read:stops'],
        rateLimit: { perMinute: 60, perHour: 1000, perDay: 10000 },
        lastUsed: new Date().toISOString(),
        expiresAt: new Date(Date.now() + 30 * 24 * 60 * 60 * 1000).toISOString(),
        createdAt: new Date(Date.now() - 15 * 24 * 60 * 60 * 1000).toISOString(),
        isActive: true,
      },
    ];
    setApiKeys(mockKeys);
  };

  const handleCreateKey = async () => {
    if (!newKeyName || selectedPermissions.length === 0) {
      return;
    }

    // TODO: Create API key via backend
    const newKey: APIKey = {
      id: String(apiKeys.length + 1),
      name: newKeyName,
      key: `sk_live_${Math.random().toString(36).substring(2, 18)}`,
      keyPreview: 'sk_live_...xxxx',
      permissions: selectedPermissions,
      rateLimit: { perMinute: 60, perHour: 1000, perDay: 10000 },
      lastUsed: null,
      expiresAt: null,
      createdAt: new Date().toISOString(),
      isActive: true,
    };

    setApiKeys([...apiKeys, newKey]);
    setShowNewKeyModal(false);
    setNewKeyName('');
    setSelectedPermissions([]);
  };

  const handleDeleteKey = async (keyId: string) => {
    if (confirm('Are you sure you want to delete this API key? This action cannot be undone.')) {
      // TODO: Delete API key via backend
      setApiKeys(apiKeys.filter((key) => key.id !== keyId));
    }
  };

  const handleCopyKey = (key: string, keyId: string) => {
    navigator.clipboard.writeText(key);
    setCopiedKeyId(keyId);
    setTimeout(() => setCopiedKeyId(null), 2000);
  };

  const handleToggleKeyStatus = async (keyId: string) => {
    // TODO: Toggle API key status via backend
    setApiKeys(
      apiKeys.map((key) => (key.id === keyId ? { ...key, isActive: !key.isActive } : key))
    );
  };

  return (
    <div id="api-key-manager" className="space-y-6">
      {/* Header */}
      <div id="api-key-header" className="bg-white rounded-lg shadow p-6">
        <div className="flex items-center justify-between">
          <div>
            <h3 className="text-lg font-medium text-gray-900">API Keys</h3>
            <p className="mt-1 text-sm text-gray-500">
              Manage API keys for programmatic access to the MARTA Analytics Platform
            </p>
          </div>
          <button
            id="create-key-button"
            onClick={() => setShowNewKeyModal(true)}
            className="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md shadow-sm text-white bg-blue-600 hover:bg-blue-700"
          >
            <Plus className="h-4 w-4 mr-2" />
            Create New Key
          </button>
        </div>
      </div>

      {/* API Keys List */}
      <div id="api-keys-list" className="space-y-4">
        {apiKeys.map((apiKey) => (
          <div
            key={apiKey.id}
            id={`api-key-${apiKey.id}`}
            className="bg-white rounded-lg shadow p-6"
          >
            <div className="flex items-start justify-between">
              <div className="flex-1">
                <div className="flex items-center">
                  <Key className="h-5 w-5 text-gray-400 mr-2" />
                  <h4 className="text-base font-medium text-gray-900">{apiKey.name}</h4>
                  {!apiKey.isActive && (
                    <span className="ml-2 px-2 py-1 text-xs font-medium bg-gray-100 text-gray-800 rounded-full">
                      Disabled
                    </span>
                  )}
                </div>

                <div className="mt-2 flex items-center space-x-4 text-sm text-gray-500">
                  <span>Key: {apiKey.keyPreview}</span>
                  <button
                    onClick={() => handleCopyKey(apiKey.key, apiKey.id)}
                    className="text-blue-600 hover:text-blue-700 flex items-center"
                  >
                    <Copy className="h-4 w-4 mr-1" />
                    {copiedKeyId === apiKey.id ? 'Copied!' : 'Copy'}
                  </button>
                </div>

                <div className="mt-3">
                  <span className="text-sm text-gray-500">Permissions: </span>
                  <div className="inline-flex flex-wrap gap-2 mt-1">
                    {apiKey.permissions.map((permission) => (
                      <span
                        key={permission}
                        className="px-2 py-1 text-xs font-medium bg-blue-100 text-blue-800 rounded"
                      >
                        {permission}
                      </span>
                    ))}
                  </div>
                </div>

                <div className="mt-3 grid grid-cols-2 sm:grid-cols-4 gap-4 text-sm">
                  <div>
                    <span className="text-gray-500">Rate Limit:</span>
                    <p className="font-medium text-gray-900">
                      {apiKey.rateLimit.perMinute}/min
                    </p>
                  </div>
                  <div>
                    <span className="text-gray-500">Last Used:</span>
                    <p className="font-medium text-gray-900">
                      {apiKey.lastUsed
                        ? new Date(apiKey.lastUsed).toLocaleString()
                        : 'Never'}
                    </p>
                  </div>
                  <div>
                    <span className="text-gray-500">Created:</span>
                    <p className="font-medium text-gray-900">
                      {new Date(apiKey.createdAt).toLocaleDateString()}
                    </p>
                  </div>
                  <div>
                    <span className="text-gray-500">Expires:</span>
                    <p className="font-medium text-gray-900">
                      {apiKey.expiresAt
                        ? new Date(apiKey.expiresAt).toLocaleDateString()
                        : 'Never'}
                    </p>
                  </div>
                </div>
              </div>

              <div className="flex items-center space-x-2">
                <button
                  onClick={() => handleToggleKeyStatus(apiKey.id)}
                  className={`p-2 rounded-md ${
                    apiKey.isActive
                      ? 'text-gray-400 hover:text-gray-500'
                      : 'text-green-600 hover:text-green-700'
                  }`}
                >
                  {apiKey.isActive ? (
                    <EyeOff className="h-5 w-5" />
                  ) : (
                    <Eye className="h-5 w-5" />
                  )}
                </button>
                <button
                  onClick={() => handleDeleteKey(apiKey.id)}
                  className="p-2 text-red-400 hover:text-red-500"
                >
                  <Trash2 className="h-5 w-5" />
                </button>
              </div>
            </div>
          </div>
        ))}
      </div>

      {/* Create New Key Modal */}
      {showNewKeyModal && (
        <div id="new-key-modal" className="fixed inset-0 bg-gray-500 bg-opacity-75 flex items-center justify-center p-4">
          <div className="bg-white rounded-lg max-w-md w-full p-6">
            <h3 className="text-lg font-medium text-gray-900 mb-4">Create New API Key</h3>

            <div className="space-y-4">
              <div>
                <label htmlFor="key-name" className="block text-sm font-medium text-gray-700">
                  Key Name
                </label>
                <input
                  id="key-name"
                  type="text"
                  value={newKeyName}
                  onChange={(e) => setNewKeyName(e.target.value)}
                  className="mt-1 block w-full border-gray-300 rounded-md shadow-sm focus:ring-blue-500 focus:border-blue-500 sm:text-sm"
                  placeholder="e.g., Production API"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Permissions
                </label>
                <div className="space-y-2">
                  {availablePermissions.map((permission) => (
                    <label key={permission} className="flex items-center">
                      <input
                        type="checkbox"
                        value={permission}
                        checked={selectedPermissions.includes(permission)}
                        onChange={(e) => {
                          if (e.target.checked) {
                            setSelectedPermissions([...selectedPermissions, permission]);
                          } else {
                            setSelectedPermissions(
                              selectedPermissions.filter((p) => p !== permission)
                            );
                          }
                        }}
                        className="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
                      />
                      <span className="ml-2 text-sm text-gray-700">{permission}</span>
                    </label>
                  ))}
                </div>
              </div>
            </div>

            <div className="mt-6 flex justify-end space-x-3">
              <button
                onClick={() => setShowNewKeyModal(false)}
                className="px-4 py-2 border border-gray-300 rounded-md text-sm font-medium text-gray-700 hover:bg-gray-50"
              >
                Cancel
              </button>
              <button
                onClick={handleCreateKey}
                disabled={!newKeyName || selectedPermissions.length === 0}
                className="px-4 py-2 border border-transparent text-sm font-medium rounded-md text-white bg-blue-600 hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                Create Key
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default APIKeyManager;