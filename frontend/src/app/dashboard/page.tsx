export default function Dashboard() {
  return (
    <div className="bg-white shadow rounded-lg">
      <div className="px-4 py-5 sm:p-6">
        <h2 className="text-lg font-medium leading-6 text-gray-900">Dashboard</h2>
        <div className="mt-2 max-w-xl text-sm text-gray-500">
          <p>
            This is a protected dashboard page. You can still access it without logging in
            during development, but in production, it would require authentication.
          </p>
        </div>
        <div className="mt-5">
          <div className="rounded-md bg-gray-50 px-6 py-5 sm:flex sm:items-start sm:justify-between">
            <div className="sm:flex sm:items-start">
              <div className="mt-3 sm:mt-0 sm:ml-4">
                <div className="text-sm font-medium text-gray-900">Development Features</div>
                <div className="mt-1 text-sm text-gray-600">
                  <ul className="list-disc pl-5 space-y-1">
                    <li>Quick login with dev@example.com/dev</li>
                    <li>Auto-activation of new accounts</li>
                    <li>Relaxed authentication in development</li>
                    <li>Real-time API updates with hot reload</li>
                  </ul>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
