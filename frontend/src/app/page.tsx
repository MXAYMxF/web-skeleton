export default function Home() {
  return (
    <div className="max-w-7xl mx-auto py-16 px-4 sm:py-24 sm:px-6 lg:px-8">
      <div className="text-center">
        <h1 className="text-4xl font-bold tracking-tight text-gray-900 sm:text-5xl md:text-6xl">
          <span className="block">Welcome to</span>
          <span className="block text-indigo-600">Web Skeleton</span>
        </h1>
        <p className="mt-3 max-w-md mx-auto text-base text-gray-500 sm:text-lg md:mt-5 md:text-xl md:max-w-3xl">
          A modern, production-ready web application skeleton built with Next.js and FastAPI.
          Get started building your next big project with best practices baked in.
        </p>
        <div className="mt-5 max-w-md mx-auto sm:flex sm:justify-center md:mt-8">
          <div className="rounded-md shadow">
            <a
              href="/dashboard"
              className="w-full flex items-center justify-center px-8 py-3 border border-transparent text-base font-medium rounded-md text-white bg-indigo-600 hover:bg-indigo-700 md:py-4 md:text-lg md:px-10"
            >
              Get started
            </a>
          </div>
          <div className="mt-3 rounded-md shadow sm:mt-0 sm:ml-3">
            <a
              href="https://github.com/MXAYMxF/web-skeleton"
              target="_blank"
              rel="noopener noreferrer"
              className="w-full flex items-center justify-center px-8 py-3 border border-transparent text-base font-medium rounded-md text-indigo-600 bg-white hover:bg-gray-50 md:py-4 md:text-lg md:px-10"
            >
              View on GitHub
            </a>
          </div>
        </div>
      </div>

      <div className="mt-24">
        <dl className="space-y-10 md:space-y-0 md:grid md:grid-cols-3 md:gap-x-8 md:gap-y-10">
          {[
            {
              title: 'Modern Stack',
              description: 'Built with Next.js, FastAPI, PostgreSQL, and Redis for optimal performance and developer experience.'
            },
            {
              title: 'Developer Friendly',
              description: 'Includes authentication, database migrations, API documentation, and comprehensive testing setup.'
            },
            {
              title: 'Production Ready',
              description: 'Follows best practices for security, scalability, and maintainability right out of the box.'
            }
          ].map((feature) => (
            <div key={feature.title} className="relative">
              <dt>
                <p className="text-lg leading-6 font-medium text-gray-900">{feature.title}</p>
              </dt>
              <dd className="mt-2 text-base text-gray-500">{feature.description}</dd>
            </div>
          ))}
        </dl>
      </div>
    </div>
  );
}
