'use client';

import { useCallback, useEffect, useState } from 'react';
import axios from 'axios';
import toast from 'react-hot-toast';
import { admin, settings, type AdminUser, type AppSettings } from '@/utils/api';
import { useAuthStore } from '@/stores/useAuthStore';

const PAGE_SIZE = 20;

// Pull a human-readable message out of an axios error, falling back gracefully.
function errorDetail(error: unknown, fallback: string): string {
  if (axios.isAxiosError(error)) {
    // The API wraps errors as { error: { detail } }; also tolerate a plain { detail }.
    const data = error.response?.data as
      | { detail?: unknown; error?: { detail?: unknown } }
      | undefined;
    const detail = data?.error?.detail ?? data?.detail;
    if (typeof detail === 'string') {
      return detail;
    }
  }
  return fallback;
}

export default function AdminPage() {
  const { user, isAuthenticated } = useAuthStore();

  const [users, setUsers] = useState<AdminUser[]>([]);
  const [total, setTotal] = useState(0);
  const [skip, setSkip] = useState(0);
  const [loading, setLoading] = useState(false);

  // Search: `searchInput` is the live field value, `query` is what we actually fetch with.
  const [searchInput, setSearchInput] = useState('');
  const [query, setQuery] = useState('');

  // Track which rows have an in-flight update so we can disable their controls.
  const [pendingIds, setPendingIds] = useState<Set<number>>(new Set());

  // Create-user form.
  const [newEmail, setNewEmail] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [newFullName, setNewFullName] = useState('');
  const [newIsActive, setNewIsActive] = useState(true);
  const [newIsSuperuser, setNewIsSuperuser] = useState(false);
  const [creating, setCreating] = useState(false);

  // Application settings form.
  const [siteName, setSiteName] = useState('');
  const [registrationOpen, setRegistrationOpen] = useState(false);
  const [maintenanceMode, setMaintenanceMode] = useState(false);
  const [settingsLoading, setSettingsLoading] = useState(false);
  const [settingsSaving, setSettingsSaving] = useState(false);

  const isSuperuser = isAuthenticated && user?.is_superuser === true;

  const loadUsers = useCallback(async () => {
    setLoading(true);
    try {
      const data = await admin.listUsers({ skip, limit: PAGE_SIZE, q: query || undefined });
      setUsers(data.items);
      setTotal(data.total);
    } catch (error) {
      console.error('Failed to load users:', error);
      toast.error(errorDetail(error, 'Failed to load users.'));
    } finally {
      setLoading(false);
    }
  }, [skip, query]);

  useEffect(() => {
    if (!isSuperuser) return;
    loadUsers();
  }, [isSuperuser, loadUsers]);

  const applySettings = useCallback((s: AppSettings) => {
    setSiteName(s.site_name);
    setRegistrationOpen(s.registration_open);
    setMaintenanceMode(s.maintenance_mode);
  }, []);

  const loadSettings = useCallback(async () => {
    setSettingsLoading(true);
    try {
      applySettings(await settings.getSettings());
    } catch (error) {
      console.error('Failed to load settings:', error);
      toast.error(errorDetail(error, 'Failed to load settings.'));
    } finally {
      setSettingsLoading(false);
    }
  }, [applySettings]);

  useEffect(() => {
    if (!isSuperuser) return;
    loadSettings();
  }, [isSuperuser, loadSettings]);

  if (!isAuthenticated) {
    return (
      <div className="bg-white shadow rounded-lg">
        <div className="px-4 py-5 sm:p-6">
          <h2 className="text-lg font-medium leading-6 text-gray-900">Admin</h2>
          <p className="mt-2 text-sm text-gray-500">Please sign in.</p>
        </div>
      </div>
    );
  }

  if (!isSuperuser) {
    return (
      <div className="bg-white shadow rounded-lg">
        <div className="px-4 py-5 sm:p-6">
          <h2 className="text-lg font-medium leading-6 text-gray-900">Admin</h2>
          <p className="mt-2 text-sm text-gray-500">
            You don&apos;t have permission to view this page.
          </p>
        </div>
      </div>
    );
  }

  const setPending = (id: number, value: boolean) => {
    setPendingIds((prev) => {
      const next = new Set(prev);
      if (value) next.add(id);
      else next.delete(id);
      return next;
    });
  };

  const handleSearchSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setSkip(0);
    setQuery(searchInput.trim());
  };

  const updateUser = async (
    id: number,
    data: { is_active?: boolean; is_superuser?: boolean },
    successMessage: string
  ) => {
    setPending(id, true);
    try {
      const updated = await admin.updateUser(id, data);
      setUsers((prev) => prev.map((u) => (u.id === id ? updated : u)));
      toast.success(successMessage);
    } catch (error) {
      console.error('Failed to update user:', error);
      toast.error(errorDetail(error, 'Failed to update user.'));
    } finally {
      setPending(id, false);
    }
  };

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newEmail.trim() || !newPassword) {
      toast.error('Email and password are required.');
      return;
    }
    setCreating(true);
    try {
      await admin.createUser({
        email: newEmail.trim(),
        password: newPassword,
        full_name: newFullName.trim() ? newFullName.trim() : undefined,
        is_active: newIsActive,
        is_superuser: newIsSuperuser,
      });
      toast.success('User created.');
      setNewEmail('');
      setNewPassword('');
      setNewFullName('');
      setNewIsActive(true);
      setNewIsSuperuser(false);
      // Jump back to the first page and refresh so the new user is visible.
      if (skip !== 0) setSkip(0);
      else await loadUsers();
    } catch (error) {
      console.error('Failed to create user:', error);
      toast.error(errorDetail(error, 'Failed to create user.'));
    } finally {
      setCreating(false);
    }
  };

  const handleSaveSettings = async (e: React.FormEvent) => {
    e.preventDefault();
    setSettingsSaving(true);
    try {
      const updated = await settings.updateSettings({
        site_name: siteName.trim(),
        registration_open: registrationOpen,
        maintenance_mode: maintenanceMode,
      });
      applySettings(updated);
      toast.success('Settings saved.');
    } catch (error) {
      console.error('Failed to save settings:', error);
      toast.error(errorDetail(error, 'Failed to save settings.'));
    } finally {
      setSettingsSaving(false);
    }
  };

  const start = total === 0 ? 0 : skip + 1;
  const end = Math.min(skip + PAGE_SIZE, total);
  const canPrev = skip > 0;
  const canNext = skip + PAGE_SIZE < total;

  const inputClass =
    'mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 shadow-sm focus:border-indigo-500 focus:outline-none focus:ring-indigo-500 sm:text-sm';
  const primaryButtonClass =
    'rounded-md bg-indigo-600 px-3 py-2 text-sm font-semibold text-white shadow-sm hover:bg-indigo-500 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-indigo-600 disabled:opacity-50';
  const secondaryButtonClass =
    'rounded-md bg-white px-2.5 py-1.5 text-xs font-semibold text-gray-900 shadow-sm ring-1 ring-inset ring-gray-300 hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed';

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold leading-6 text-gray-900">Admin</h1>
        <p className="mt-2 text-sm text-gray-500">Manage users.</p>
      </div>

      {/* Users table */}
      <section className="bg-white shadow rounded-lg">
        <div className="px-4 py-5 sm:p-6 space-y-4">
          <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
            <h2 className="text-lg font-medium leading-6 text-gray-900">Users</h2>
            <form onSubmit={handleSearchSubmit} className="flex items-center gap-2">
              <input
                type="text"
                value={searchInput}
                onChange={(e) => setSearchInput(e.target.value)}
                placeholder="Search email or name"
                className="block w-64 rounded-md border border-gray-300 px-3 py-2 shadow-sm focus:border-indigo-500 focus:outline-none focus:ring-indigo-500 sm:text-sm"
              />
              <button type="submit" className={primaryButtonClass} disabled={loading}>
                Search
              </button>
            </form>
          </div>

          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-gray-200">
              <thead>
                <tr>
                  <th className="px-3 py-2 text-left text-xs font-medium uppercase tracking-wide text-gray-500">
                    ID
                  </th>
                  <th className="px-3 py-2 text-left text-xs font-medium uppercase tracking-wide text-gray-500">
                    Email
                  </th>
                  <th className="px-3 py-2 text-left text-xs font-medium uppercase tracking-wide text-gray-500">
                    Full name
                  </th>
                  <th className="px-3 py-2 text-left text-xs font-medium uppercase tracking-wide text-gray-500">
                    Active
                  </th>
                  <th className="px-3 py-2 text-left text-xs font-medium uppercase tracking-wide text-gray-500">
                    Superuser
                  </th>
                  <th className="px-3 py-2 text-left text-xs font-medium uppercase tracking-wide text-gray-500">
                    Actions
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-200">
                {users.length === 0 && !loading ? (
                  <tr>
                    <td colSpan={6} className="px-3 py-6 text-center text-sm text-gray-500">
                      No users found.
                    </td>
                  </tr>
                ) : (
                  users.map((u) => {
                    const isSelf = u.id === user?.id;
                    const isPending = pendingIds.has(u.id);
                    const selfTitle = "You can't change your own role or status.";
                    return (
                      <tr key={u.id}>
                        <td className="px-3 py-2 text-sm text-gray-500">{u.id}</td>
                        <td className="px-3 py-2 text-sm text-gray-900">{u.email}</td>
                        <td className="px-3 py-2 text-sm text-gray-500">{u.full_name ?? '—'}</td>
                        <td className="px-3 py-2 text-sm">
                          <span
                            className={
                              u.is_active
                                ? 'inline-flex rounded-full bg-green-100 px-2 text-xs font-semibold leading-5 text-green-800'
                                : 'inline-flex rounded-full bg-gray-100 px-2 text-xs font-semibold leading-5 text-gray-600'
                            }
                          >
                            {u.is_active ? 'Active' : 'Inactive'}
                          </span>
                        </td>
                        <td className="px-3 py-2 text-sm">
                          <span
                            className={
                              u.is_superuser
                                ? 'inline-flex rounded-full bg-indigo-100 px-2 text-xs font-semibold leading-5 text-indigo-800'
                                : 'inline-flex rounded-full bg-gray-100 px-2 text-xs font-semibold leading-5 text-gray-600'
                            }
                          >
                            {u.is_superuser ? 'Yes' : 'No'}
                          </span>
                        </td>
                        <td className="px-3 py-2 text-sm">
                          <div className="flex flex-wrap gap-2">
                            <button
                              type="button"
                              className={secondaryButtonClass}
                              disabled={isSelf || isPending}
                              title={isSelf ? selfTitle : undefined}
                              onClick={() =>
                                updateUser(
                                  u.id,
                                  { is_active: !u.is_active },
                                  u.is_active ? 'User deactivated.' : 'User activated.'
                                )
                              }
                            >
                              {u.is_active ? 'Deactivate' : 'Activate'}
                            </button>
                            <button
                              type="button"
                              className={secondaryButtonClass}
                              disabled={isSelf || isPending}
                              title={isSelf ? selfTitle : undefined}
                              onClick={() =>
                                updateUser(
                                  u.id,
                                  { is_superuser: !u.is_superuser },
                                  u.is_superuser
                                    ? 'Removed superuser.'
                                    : 'Granted superuser.'
                                )
                              }
                            >
                              {u.is_superuser ? 'Remove superuser' : 'Make superuser'}
                            </button>
                          </div>
                        </td>
                      </tr>
                    );
                  })
                )}
              </tbody>
            </table>
          </div>

          <div className="flex items-center justify-between">
            <p className="text-sm text-gray-500">
              {loading
                ? 'Loading…'
                : total === 0
                  ? 'No users'
                  : `Showing ${start}–${end} of ${total}`}
            </p>
            <div className="flex gap-2">
              <button
                type="button"
                className={secondaryButtonClass}
                disabled={!canPrev || loading}
                onClick={() => setSkip(Math.max(0, skip - PAGE_SIZE))}
              >
                Prev
              </button>
              <button
                type="button"
                className={secondaryButtonClass}
                disabled={!canNext || loading}
                onClick={() => setSkip(skip + PAGE_SIZE)}
              >
                Next
              </button>
            </div>
          </div>
        </div>
      </section>

      {/* Create user */}
      <section className="bg-white shadow rounded-lg">
        <div className="px-4 py-5 sm:p-6">
          <h2 className="text-lg font-medium leading-6 text-gray-900">Create user</h2>
          <form onSubmit={handleCreate} className="mt-4 space-y-4 max-w-lg">
            <div>
              <label htmlFor="new_email" className="block text-sm font-medium text-gray-700">
                Email
              </label>
              <input
                type="email"
                id="new_email"
                value={newEmail}
                onChange={(e) => setNewEmail(e.target.value)}
                className={inputClass}
                required
              />
            </div>
            <div>
              <label htmlFor="new_password" className="block text-sm font-medium text-gray-700">
                Password
              </label>
              <input
                type="password"
                id="new_password"
                value={newPassword}
                onChange={(e) => setNewPassword(e.target.value)}
                className={inputClass}
                autoComplete="new-password"
                required
              />
            </div>
            <div>
              <label htmlFor="new_full_name" className="block text-sm font-medium text-gray-700">
                Full name
              </label>
              <input
                type="text"
                id="new_full_name"
                value={newFullName}
                onChange={(e) => setNewFullName(e.target.value)}
                className={inputClass}
              />
            </div>
            <div className="flex items-center gap-6">
              <label className="flex items-center gap-2 text-sm text-gray-700">
                <input
                  type="checkbox"
                  checked={newIsActive}
                  onChange={(e) => setNewIsActive(e.target.checked)}
                  className="h-4 w-4 rounded border-gray-300 text-indigo-600 focus:ring-indigo-500"
                />
                Active
              </label>
              <label className="flex items-center gap-2 text-sm text-gray-700">
                <input
                  type="checkbox"
                  checked={newIsSuperuser}
                  onChange={(e) => setNewIsSuperuser(e.target.checked)}
                  className="h-4 w-4 rounded border-gray-300 text-indigo-600 focus:ring-indigo-500"
                />
                Superuser
              </label>
            </div>
            <div>
              <button type="submit" disabled={creating} className={primaryButtonClass}>
                {creating ? 'Creating…' : 'Create user'}
              </button>
            </div>
          </form>
        </div>
      </section>

      {/* Application settings */}
      <section className="bg-white shadow rounded-lg">
        <div className="px-4 py-5 sm:p-6">
          <h2 className="text-lg font-medium leading-6 text-gray-900">Application settings</h2>
          <form onSubmit={handleSaveSettings} className="mt-4 space-y-4 max-w-lg">
            <div>
              <label htmlFor="site_name" className="block text-sm font-medium text-gray-700">
                Site name
              </label>
              <input
                type="text"
                id="site_name"
                value={siteName}
                onChange={(e) => setSiteName(e.target.value)}
                className={inputClass}
                disabled={settingsLoading}
              />
            </div>
            <div>
              <label className="flex items-center gap-2 text-sm text-gray-700">
                <input
                  type="checkbox"
                  checked={registrationOpen}
                  onChange={(e) => setRegistrationOpen(e.target.checked)}
                  className="h-4 w-4 rounded border-gray-300 text-indigo-600 focus:ring-indigo-500"
                  disabled={settingsLoading}
                />
                Registration open
              </label>
              <p className="mt-1 text-xs text-gray-500">
                When off, new users can&apos;t self-register.
              </p>
            </div>
            <div>
              <label className="flex items-center gap-2 text-sm text-gray-700">
                <input
                  type="checkbox"
                  checked={maintenanceMode}
                  onChange={(e) => setMaintenanceMode(e.target.checked)}
                  className="h-4 w-4 rounded border-gray-300 text-indigo-600 focus:ring-indigo-500"
                  disabled={settingsLoading}
                />
                Maintenance mode
              </label>
              <p className="mt-1 text-xs text-gray-500">
                When on, non-superusers get a 503; health, login, and public settings stay
                reachable.
              </p>
            </div>
            <div>
              <button
                type="submit"
                disabled={settingsLoading || settingsSaving}
                className={primaryButtonClass}
              >
                {settingsSaving ? 'Saving…' : 'Save settings'}
              </button>
            </div>
          </form>
        </div>
      </section>
    </div>
  );
}
