'use client';

import { Fragment, useEffect, useState } from 'react';
import { Dialog, Transition } from '@headlessui/react';
import { XMarkIcon } from '@heroicons/react/24/outline';
import toast from 'react-hot-toast';
import { auth } from '@/utils/api';
import { useAuthStore } from '@/stores/useAuthStore';

type AuthMode = 'login' | 'register';

interface LoginModalProps {
  isOpen: boolean;
  onClose: () => void;
  initialMode?: AuthMode;
}

export default function LoginModal({ isOpen, onClose, initialMode = 'login' }: LoginModalProps) {
  const [mode, setMode] = useState<AuthMode>(initialMode);
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [fullName, setFullName] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const setAuth = useAuthStore((state) => state.setAuth);

  // Sync to the requested mode (and clear stale input) each time the modal opens.
  useEffect(() => {
    if (isOpen) {
      setMode(initialMode);
      setEmail('');
      setPassword('');
      setFullName('');
    }
  }, [isOpen, initialMode]);

  const resetForm = () => {
    setEmail('');
    setPassword('');
    setFullName('');
  };

  const switchMode = (next: AuthMode) => {
    setMode(next);
    resetForm();
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsLoading(true);

    try {
      if (mode === 'register') {
        const response = await auth.register({
          email,
          password,
          full_name: fullName.trim() ? fullName.trim() : undefined,
        });
        setAuth(response.access_token, response.user);
        toast.success('Account created successfully!');
      } else {
        const response = await auth.login(email, password);
        setAuth(response.access_token, response.user);
        toast.success('Logged in successfully!');
      }
      onClose();
    } catch (error) {
      if (mode === 'register') {
        console.error('Register error:', error);
        toast.error('Failed to create account. Please try again.');
      } else {
        console.error('Login error:', error);
        toast.error('Failed to login. Please try again.');
      }
    } finally {
      setIsLoading(false);
    }
  };

  const handleQuickLogin = async () => {
    setIsLoading(true);
    try {
      const response = await auth.login('dev@example.com', 'dev');
      setAuth(response.access_token, response.user);
      toast.success('Quick login successful!');
      onClose();
    } catch (error) {
      console.error('Quick login error:', error);
      toast.error('Failed to quick login. Please try again.');
    } finally {
      setIsLoading(false);
    }
  };

  const isRegister = mode === 'register';

  return (
    <Transition.Root show={isOpen} as={Fragment}>
      <Dialog as="div" className="relative z-50" onClose={onClose}>
        <Transition.Child
          as={Fragment}
          enter="ease-out duration-300"
          enterFrom="opacity-0"
          enterTo="opacity-100"
          leave="ease-in duration-200"
          leaveFrom="opacity-100"
          leaveTo="opacity-0"
        >
          <div className="fixed inset-0 bg-gray-500 bg-opacity-75 transition-opacity" />
        </Transition.Child>

        <div className="fixed inset-0 z-10 overflow-y-auto">
          <div className="flex min-h-full items-end justify-center p-4 text-center sm:items-center sm:p-0">
            <Transition.Child
              as={Fragment}
              enter="ease-out duration-300"
              enterFrom="opacity-0 translate-y-4 sm:translate-y-0 sm:scale-95"
              enterTo="opacity-100 translate-y-0 sm:scale-100"
              leave="ease-in duration-200"
              leaveFrom="opacity-100 translate-y-0 sm:scale-100"
              leaveTo="opacity-0 translate-y-4 sm:translate-y-0 sm:scale-95"
            >
              <Dialog.Panel className="relative transform overflow-hidden rounded-lg bg-white px-4 pb-4 pt-5 text-left shadow-xl transition-all sm:my-8 sm:w-full sm:max-w-sm sm:p-6">
                <div className="absolute right-0 top-0 pr-4 pt-4">
                  <button
                    type="button"
                    className="rounded-md bg-white text-gray-400 hover:text-gray-500"
                    onClick={onClose}
                  >
                    <span className="sr-only">Close</span>
                    <XMarkIcon className="h-6 w-6" aria-hidden="true" />
                  </button>
                </div>
                <div>
                  <Dialog.Title as="h3" className="text-lg font-semibold leading-6 text-gray-900 mb-4">
                    {isRegister ? 'Sign Up' : 'Sign In'}
                  </Dialog.Title>
                  <form onSubmit={handleSubmit} className="space-y-4">
                    {isRegister && (
                      <div>
                        <label htmlFor="full_name" className="block text-sm font-medium text-gray-700">
                          Full name <span className="text-gray-400">(optional)</span>
                        </label>
                        <input
                          type="text"
                          id="full_name"
                          value={fullName}
                          onChange={(e) => setFullName(e.target.value)}
                          className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 shadow-sm focus:border-indigo-500 focus:outline-none focus:ring-indigo-500 sm:text-sm"
                        />
                      </div>
                    )}
                    <div>
                      <label htmlFor="email" className="block text-sm font-medium text-gray-700">
                        Email
                      </label>
                      <input
                        type="email"
                        id="email"
                        value={email}
                        onChange={(e) => setEmail(e.target.value)}
                        className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 shadow-sm focus:border-indigo-500 focus:outline-none focus:ring-indigo-500 sm:text-sm"
                        required
                      />
                    </div>
                    <div>
                      <label htmlFor="password" className="block text-sm font-medium text-gray-700">
                        Password
                      </label>
                      <input
                        type="password"
                        id="password"
                        value={password}
                        onChange={(e) => setPassword(e.target.value)}
                        className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 shadow-sm focus:border-indigo-500 focus:outline-none focus:ring-indigo-500 sm:text-sm"
                        required
                      />
                    </div>
                    <div className="flex flex-col gap-2">
                      <button
                        type="submit"
                        disabled={isLoading}
                        className="w-full rounded-md bg-indigo-600 px-3 py-2 text-sm font-semibold text-white shadow-sm hover:bg-indigo-500 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-indigo-600 disabled:opacity-50"
                      >
                        {isRegister
                          ? isLoading
                            ? 'Creating account...'
                            : 'Create account'
                          : isLoading
                            ? 'Signing in...'
                            : 'Sign in'}
                      </button>
                      {!isRegister && (
                        <button
                          type="button"
                          onClick={handleQuickLogin}
                          disabled={isLoading}
                          className="w-full rounded-md bg-gray-100 px-3 py-2 text-sm font-semibold text-gray-900 shadow-sm hover:bg-gray-200 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-gray-300 disabled:opacity-50"
                        >
                          Quick Dev Login
                        </button>
                      )}
                    </div>
                  </form>
                  <p className="mt-4 text-center text-sm text-gray-600">
                    {isRegister ? (
                      <>
                        Already have an account?{' '}
                        <button
                          type="button"
                          onClick={() => switchMode('login')}
                          className="font-semibold text-indigo-600 hover:text-indigo-500"
                        >
                          Sign in
                        </button>
                      </>
                    ) : (
                      <>
                        Don&apos;t have an account?{' '}
                        <button
                          type="button"
                          onClick={() => switchMode('register')}
                          className="font-semibold text-indigo-600 hover:text-indigo-500"
                        >
                          Sign up
                        </button>
                      </>
                    )}
                  </p>
                </div>
              </Dialog.Panel>
            </Transition.Child>
          </div>
        </div>
      </Dialog>
    </Transition.Root>
  );
}
