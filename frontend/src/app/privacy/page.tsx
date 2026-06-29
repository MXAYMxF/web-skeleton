export const metadata = { title: 'Privacy Policy' };

export default function PrivacyPolicy() {
  return (
    <div className="max-w-3xl mx-auto py-16 px-4 sm:px-6 lg:px-8">
      <h1 className="text-3xl font-bold tracking-tight text-gray-900 sm:text-4xl">
        Privacy Policy
      </h1>
      <p className="mt-4 text-sm text-gray-500">
        This is placeholder content for a starter template. Replace it with your
        own policy before going to production.
      </p>

      <section className="mt-10">
        <h2 className="text-xl font-semibold text-gray-900">Information We Collect</h2>
        <p className="mt-2 text-base text-gray-500">
          Describe the data you collect from users — for example account details,
          usage analytics, and any information provided directly. Be specific about
          what is required versus optional.
        </p>
      </section>

      <section className="mt-8">
        <h2 className="text-xl font-semibold text-gray-900">How We Use It</h2>
        <p className="mt-2 text-base text-gray-500">
          Explain the purposes for processing data, such as providing the service,
          improving features, and communicating with users. Avoid using data in ways
          you have not disclosed here.
        </p>
      </section>

      <section className="mt-8">
        <h2 className="text-xl font-semibold text-gray-900">Data Sharing</h2>
        <p className="mt-2 text-base text-gray-500">
          State whether and how you share data with third parties, such as
          infrastructure providers or analytics services, and under what conditions.
        </p>
      </section>

      <section className="mt-8">
        <h2 className="text-xl font-semibold text-gray-900">Contact</h2>
        <p className="mt-2 text-base text-gray-500">
          Tell users how to reach you with privacy questions or requests to access or
          delete their data. Replace this with a real contact address.
        </p>
      </section>
    </div>
  );
}
