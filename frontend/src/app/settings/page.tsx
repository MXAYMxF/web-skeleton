'use client';

import { useEffect, useState } from 'react';
import axios from 'axios';
import toast from 'react-hot-toast';
import { users } from '@/utils/api';
import { useAuthStore } from '@/stores/useAuthStore';

type ThemePreference = 'light' | 'dark' | 'system';

const THEME_OPTIONS: { value: ThemePreference; label: string }[] = [
  { value: 'light', label: 'Light' },
  { value: 'dark', label: 'Dark' },
  { value: 'system', label: 'System' },
];

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

export default function SettingsPage() {
  const { token, user, isAuthenticated, setAuth } = useAuthStore();

  // Profile form
  const [fullName, setFullName] = useState('');
  const [email, setEmail] = useState('');
  const [savingProfile, setSavingProfile] = useState(false);

  // Password form
  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [savingPassword, setSavingPassword] = useState(false);

  // Preferences
  const [preferences, setPreferences] = useState<Record<string, unknown>>({});
  const [theme, setTheme] = useState<ThemePreference>('system');
  const [savingPreferences, setSavingPreferences] = useState(false);

  // Hydrate local form state from a User object.
  const hydrate = (u: typeof user) => {
    if (!u) return;
    setFullName(u.full_name ?? '');
    setEmail(u.email ?? '');
    const prefs = (u.preferences ?? {}) as Record<string, unknown>;
    setPreferences(prefs);
    const t = prefs.theme;
    setTheme(t === 'light' || t === 'dark' || t === 'system' ? t : 'system');
  };

  // Prefill immediately from the store, then refresh from the server on mount.
  useEffect(() => {
    if (!isAuthenticated) return;
    hydrate(user);
    let cancelled = false;
    (async () => {
      try {
        const me = await users.getMe();
        if (!cancelled) {
          hydrate(me);
          if (token) setAuth(token, me);
        }
      } catch (error) {
        console.error('Failed to load profile:', error);
        toast.error(errorDetail(error, 'Failed to load your profile.'));
      }
    })();
    return () => {
      cancelled = true;
    };
    // Run once on mount; store setters are stable.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isAuthenticated]);

  if (!isAuthenticated) {
    return (
      <div className="bg-white shadow rounded-lg">
        <div className="px-4 py-5 sm:p-6">
          <h2 className="text-lg font-medium leading-6 text-gray-900">Settings</h2>
          <p className="mt-2 text-sm text-gray-500">Please sign in to access settings.</p>
        </div>
      </div>
    );
  }

  const handleProfileSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSavingProfile(true);
    try {
      const updated = await users.updateMe({
        full_name: fullName.trim() ? fullName.trim() : null,
        email,
      });
      if (token) setAuth(token, updated);
      hydrate(updated);
      toast.success('Profile updated.');
    } catch (error) {
      console.error('Profile update error:', error);
      toast.error(errorDetail(error, 'Failed to update profile.'));
    } finally {
      setSavingProfile(false);
    }
  };

  const handlePasswordSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newPassword || !confirmPassword) {
      toast.error('Please fill in both password fields.');
      return;
    }
    if (newPassword !== confirmPassword) {
      toast.error('Passwords do not match.');
      return;
    }
    setSavingPassword(true);
    try {
      await users.updateMe({ password: newPassword });
      setNewPassword('');
      setConfirmPassword('');
      toast.success('Password changed.');
    } catch (error) {
      console.error('Password change error:', error);
      toast.error(errorDetail(error, 'Failed to change password.'));
    } finally {
      setSavingPassword(false);
    }
  };

  const handlePreferencesSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSavingPreferences(true);
    try {
      const nextPreferences = { ...preferences, theme };
      const updated = await users.updateMe({ preferences: nextPreferences });
      if (token) setAuth(token, updated);
      hydrate(updated);
      toast.success('Preferences saved.');
    } catch (error) {
      console.error('Preferences update error:', error);
      toast.error(errorDetail(error, 'Failed to save preferences.'));
    } finally {
      setSavingPreferences(false);
    }
  };

  const inputClass =
    'mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 shadow-sm focus:border-indigo-500 focus:outline-none focus:ring-indigo-500 sm:text-sm';
  const primaryButtonClass =
    'rounded-md bg-indigo-600 px-3 py-2 text-sm font-semibold text-white shadow-sm hover:bg-indigo-500 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-indigo-600 disabled:opacity-50';

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold leading-6 text-gray-900">Settings</h1>
        <p className="mt-2 text-sm text-gray-500">Manage your profile, password, and preferences.</p>
      </div>

      {/* Profile */}
      <section className="bg-white shadow rounded-lg">
        <div className="px-4 py-5 sm:p-6">
          <h2 className="text-lg font-medium leading-6 text-gray-900">Profile</h2>
          <form onSubmit={handleProfileSubmit} className="mt-4 space-y-4 max-w-lg">
            <div>
              <label htmlFor="full_name" className="block text-sm font-medium text-gray-700">
                Full name
              </label>
              <input
                type="text"
                id="full_name"
                value={fullName}
                onChange={(e) => setFullName(e.target.value)}
                className={inputClass}
              />
            </div>
            <div>
              <label htmlFor="email" className="block text-sm font-medium text-gray-700">
                Email
              </label>
              <input
                type="email"
                id="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className={inputClass}
                required
              />
              <p className="mt-1 text-xs text-gray-500">
                Changing your email may require signing in again, since your session is tied to it.
              </p>
            </div>
            <div>
              <button type="submit" disabled={savingProfile} className={primaryButtonClass}>
                {savingProfile ? 'Saving...' : 'Save profile'}
              </button>
            </div>
          </form>
        </div>
      </section>

      {/* Change password */}
      <section className="bg-white shadow rounded-lg">
        <div className="px-4 py-5 sm:p-6">
          <h2 className="text-lg font-medium leading-6 text-gray-900">Change password</h2>
          <form onSubmit={handlePasswordSubmit} className="mt-4 space-y-4 max-w-lg">
            <div>
              <label htmlFor="new_password" className="block text-sm font-medium text-gray-700">
                New password
              </label>
              <input
                type="password"
                id="new_password"
                value={newPassword}
                onChange={(e) => setNewPassword(e.target.value)}
                className={inputClass}
                autoComplete="new-password"
              />
            </div>
            <div>
              <label htmlFor="confirm_password" className="block text-sm font-medium text-gray-700">
                Confirm new password
              </label>
              <input
                type="password"
                id="confirm_password"
                value={confirmPassword}
                onChange={(e) => setConfirmPassword(e.target.value)}
                className={inputClass}
                autoComplete="new-password"
              />
            </div>
            <div>
              <button type="submit" disabled={savingPassword} className={primaryButtonClass}>
                {savingPassword ? 'Saving...' : 'Change password'}
              </button>
            </div>
          </form>
        </div>
      </section>

      {/* Preferences */}
      <section className="bg-white shadow rounded-lg">
        <div className="px-4 py-5 sm:p-6">
          <h2 className="text-lg font-medium leading-6 text-gray-900">Preferences</h2>
          <form onSubmit={handlePreferencesSubmit} className="mt-4 space-y-4 max-w-lg">
            <div>
              <label htmlFor="theme" className="block text-sm font-medium text-gray-700">
                Theme
              </label>
              <select
                id="theme"
                value={theme}
                onChange={(e) => setTheme(e.target.value as ThemePreference)}
                className={inputClass}
              >
                {THEME_OPTIONS.map((option) => (
                  <option key={option.value} value={option.value}>
                    {option.label}
                  </option>
                ))}
              </select>
            </div>
            <div>
              <button type="submit" disabled={savingPreferences} className={primaryButtonClass}>
                {savingPreferences ? 'Saving...' : 'Save preferences'}
              </button>
            </div>
          </form>
        </div>
      </section>
    </div>
  );
}
