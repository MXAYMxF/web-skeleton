export const metadata = { title: 'Support' };

export default function Support() {
  return (
    <div className="max-w-3xl mx-auto py-16 px-4 sm:px-6 lg:px-8">
      <h1 className="text-3xl font-bold tracking-tight text-gray-900 sm:text-4xl">
        Support
      </h1>
      <p className="mt-4 text-sm text-gray-500">
        This is placeholder content for a starter template. Replace it with your own
        support details before going to production.
      </p>

      <section className="mt-10">
        <h2 className="text-xl font-semibold text-gray-900">Getting Help</h2>
        <p className="mt-2 text-base text-gray-500">
          Point users to your documentation, guides, or knowledge base as a first
          stop. Link to the resources that resolve the most common questions.
        </p>
      </section>

      <section className="mt-8">
        <h2 className="text-xl font-semibold text-gray-900">Contact Us</h2>
        <p className="mt-2 text-base text-gray-500">
          Provide the best way to reach your team — an email address, support form, or
          chat channel — along with expected response times. Replace this with real
          contact details.
        </p>
      </section>

      <section className="mt-8">
        <h2 className="text-xl font-semibold text-gray-900">FAQ</h2>
        <p className="mt-2 text-base text-gray-500">
          Collect answers to frequently asked questions here so users can self-serve.
          Add your most common questions and keep them up to date.
        </p>
      </section>
    </div>
  );
}
