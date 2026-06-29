export const metadata = { title: 'Terms & Conditions' };

export default function TermsAndConditions() {
  return (
    <div className="max-w-3xl mx-auto py-16 px-4 sm:px-6 lg:px-8">
      <h1 className="text-3xl font-bold tracking-tight text-gray-900 sm:text-4xl">
        Terms &amp; Conditions
      </h1>
      <p className="mt-4 text-sm text-gray-500">
        This is placeholder content for a starter template. Replace it with your own
        terms before going to production.
      </p>

      <section className="mt-10">
        <h2 className="text-xl font-semibold text-gray-900">Acceptance of Terms</h2>
        <p className="mt-2 text-base text-gray-500">
          By accessing or using this service, users agree to be bound by these terms.
          Note what happens if they do not agree, and how updates to the terms are
          communicated.
        </p>
      </section>

      <section className="mt-8">
        <h2 className="text-xl font-semibold text-gray-900">Use of Service</h2>
        <p className="mt-2 text-base text-gray-500">
          Outline acceptable use, account responsibilities, and any prohibited
          behavior. Clarify that users are responsible for activity under their
          accounts.
        </p>
      </section>

      <section className="mt-8">
        <h2 className="text-xl font-semibold text-gray-900">Limitation of Liability</h2>
        <p className="mt-2 text-base text-gray-500">
          Describe the limits of your liability and any disclaimers of warranties, to
          the extent permitted by applicable law. Have a lawyer review this section.
        </p>
      </section>

      <section className="mt-8">
        <h2 className="text-xl font-semibold text-gray-900">Changes</h2>
        <p className="mt-2 text-base text-gray-500">
          Explain how and when these terms may change, and how continued use
          constitutes acceptance of any revisions.
        </p>
      </section>
    </div>
  );
}
