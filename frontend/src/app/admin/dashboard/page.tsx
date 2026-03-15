'use client'

import { useState, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import Link from 'next/link'
import { API_BASE_URL } from '@/lib/apiClient';

export default function AdminDashboard() {
  const router = useRouter()
  const [userData, setUserData] = useState<any>(null)
  const [formData, setFormData] = useState({
    candidate_name: '',
    candidate_email: '',
    job_description: ''
  })
  const [resume, setResume] = useState<File | null>(null)
  const [error, setError] = useState('')
  const [success, setSuccess] = useState('')
  const [loading, setLoading] = useState(false)
  const [candidates, setCandidates] = useState<any[]>([])
  const [loadingCandidates, setLoadingCandidates] = useState(false)
  const [activeTab, setActiveTab] = useState<'register' | 'candidates'>('register')

  useEffect(() => {
    // Check if user is logged in
    const token = localStorage.getItem('token')
    const userType = localStorage.getItem('userType')
    const storedUserData = localStorage.getItem('userData')

    if (!token || userType !== 'admin') {
      router.push('/login/admin')
      return
    }

    if (storedUserData) {
      setUserData(JSON.parse(storedUserData))
    }

    // Fetch candidates on mount
    fetchCandidates()
  }, [router])

  const fetchCandidates = async () => {
    const token = localStorage.getItem('token')
    if (!token) return

    setLoadingCandidates(true)
    try {
      const res = await fetch(`${API_BASE_URL}/api/v1/auth/admin/candidates`, {
        headers: { 'Authorization': `Bearer ${token}` }
      })
      if (res.ok) setCandidates(await res.json())
    } catch (err: any) {
      console.error('Failed to fetch candidates:', err)
    } finally {
      setLoadingCandidates(false)
    }
  }

  const toggleCandidateLogin = async (candidateId: string) => {
    const token = localStorage.getItem('token')
    if (!token) return

    try {
      const res = await fetch(
        `${API_BASE_URL}/api/v1/auth/admin/candidates/${candidateId}/toggle-login`,
        { method: 'POST', headers: { 'Authorization': `Bearer ${token}`, 'Content-Type': 'application/json' }, body: '{}' }
      )
      const data = await res.json()
      setCandidates(candidates.map(c =>
        c.id === candidateId ? { ...c, login_disabled: data.login_disabled } : c
      ))
      setSuccess(data.message || 'Login status updated.')
      setTimeout(() => setSuccess(''), 3000)
    } catch (err: any) {
      setError('Failed to toggle login status')
      setTimeout(() => setError(''), 3000)
    }
  }

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) => {
    const { name, value } = e.target
    setFormData(prev => ({
      ...prev,
      [name]: value
    }))
  }

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      setResume(e.target.files[0])
    }
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')
    setSuccess('')
    setLoading(true)

    try {
      const token = localStorage.getItem('token')
      if (!token) {
        router.push('/login/admin')
        return
      }

      const formDataToSend = new FormData()
      formDataToSend.append('candidate_name', formData.candidate_name)
      formDataToSend.append('candidate_email', formData.candidate_email)
      formDataToSend.append('job_description', formData.job_description)
      if (resume) {
        formDataToSend.append('resume', resume)
      }

      const res = await fetch(`${API_BASE_URL}/api/v1/auth/admin/register-candidate`, {
        method: 'POST',
        headers: { 'Authorization': `Bearer ${token}` },
        body: formDataToSend,
      })
      if (!res.ok) {
        const errData = await res.json().catch(() => ({}))
        throw new Error(errData.detail || `Error ${res.status}`)
      }

      setSuccess(`Candidate ${formData.candidate_name} has been successfully registered! Credentials (email and password) have been sent to ${formData.candidate_email}`)

      // Reset form
      setFormData({
        candidate_name: '',
        candidate_email: '',
        job_description: ''
      })
      setResume(null)

      // Reset file input
      const fileInput = document.getElementById('resume') as HTMLInputElement
      if (fileInput) fileInput.value = ''

      // Refresh candidates list
      fetchCandidates()
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to register candidate. Please try again.')
    } finally {
      setLoading(false)
    }
  }

  const handleLogout = () => {
    localStorage.removeItem('token')
    localStorage.removeItem('userType')
    localStorage.removeItem('userData')
    router.push('/')
  }

  if (!userData) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-indigo-600 mx-auto"></div>
          <p className="mt-4 text-gray-600">Loading...</p>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-50 to-gray-100 dark:from-gray-900 dark:to-gray-800">
      {/* Header */}
      <header className="bg-white dark:bg-gray-800 shadow-sm">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
          <div className="flex justify-between items-center">
            <div>
              <h1 className="text-2xl font-bold text-gray-900 dark:text-white">Admin Dashboard</h1>
              <p className="text-sm text-gray-600 dark:text-gray-400">Welcome, {userData.email || userData.username}</p>
            </div>
            <div className="flex gap-4">
              <Link href="/" className="px-4 py-2 text-gray-700 dark:text-gray-300 hover:text-gray-900 dark:hover:text-white">
                Home
              </Link>
              <button
                onClick={handleLogout}
                className="px-4 py-2 bg-red-600 hover:bg-red-700 text-white rounded-lg transition-colors"
              >
                Logout
              </button>
            </div>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Success/Error Messages - Show in both tabs */}
        {success && (
          <div className="mb-6 p-4 bg-green-100 dark:bg-green-900 border border-green-400 text-green-700 dark:text-green-300 rounded-lg">
            {success}
          </div>
        )}

        {error && (
          <div className="mb-6 p-4 bg-red-100 dark:bg-red-900 border border-red-400 text-red-700 dark:text-red-300 rounded-lg">
            {error}
          </div>
        )}

        {/* Tabs */}
        <div className="mb-6">
          <div className="border-b border-gray-200 dark:border-gray-700">
            <nav className="-mb-px flex space-x-8">
              <button
                onClick={() => setActiveTab('register')}
                className={`py-4 px-1 border-b-2 font-medium text-sm ${activeTab === 'register'
                  ? 'border-indigo-500 text-indigo-600 dark:text-indigo-400'
                  : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300 dark:text-gray-400 dark:hover:text-gray-300'
                  }`}
              >
                Register Candidate
              </button>
              <button
                onClick={() => {
                  setActiveTab('candidates')
                  fetchCandidates()
                }}
                className={`py-4 px-1 border-b-2 font-medium text-sm ${activeTab === 'candidates'
                  ? 'border-indigo-500 text-indigo-600 dark:text-indigo-400'
                  : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300 dark:text-gray-400 dark:hover:text-gray-300'
                  }`}
              >
                Manage Candidates
              </button>
            </nav>
          </div>
        </div>

        {/* Register Candidate Tab */}
        {activeTab === 'register' && (
          <div className="bg-white dark:bg-gray-800 rounded-2xl shadow-xl p-8">
            <div className="mb-8">
              <h2 className="text-3xl font-bold text-gray-900 dark:text-white mb-2">Register New Candidate</h2>
              <p className="text-gray-600 dark:text-gray-300">
                Fill in the candidate details, job description, and upload their resume.
                Credentials (email and password) will be automatically generated and sent to the candidate's email.
              </p>
            </div>

            {/* Registration Form */}
            <form onSubmit={handleSubmit} className="space-y-6">
              <div>
                <label htmlFor="candidate_name" className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                  Candidate Name *
                </label>
                <input
                  id="candidate_name"
                  name="candidate_name"
                  type="text"
                  value={formData.candidate_name}
                  onChange={handleInputChange}
                  required
                  className="w-full px-4 py-3 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-transparent dark:bg-gray-700 dark:text-white outline-none transition"
                  placeholder="John Doe"
                />
              </div>

              <div>
                <label htmlFor="candidate_email" className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                  Candidate Email *
                </label>
                <input
                  id="candidate_email"
                  name="candidate_email"
                  type="email"
                  value={formData.candidate_email}
                  onChange={handleInputChange}
                  required
                  className="w-full px-4 py-3 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-transparent dark:bg-gray-700 dark:text-white outline-none transition"
                  placeholder="candidate@example.com"
                />
              </div>

              <div>
                <label htmlFor="job_description" className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                  Job Description *
                </label>
                <textarea
                  id="job_description"
                  name="job_description"
                  value={formData.job_description}
                  onChange={handleInputChange}
                  required
                  rows={8}
                  className="w-full px-4 py-3 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-transparent dark:bg-gray-700 dark:text-white outline-none transition resize-none"
                  placeholder="Enter the job description, requirements, and responsibilities..."
                />
              </div>

              <div>
                <label htmlFor="resume" className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                  Resume (PDF/DOC/DOCX) *
                </label>
                <input
                  id="resume"
                  name="resume"
                  type="file"
                  onChange={handleFileChange}
                  required
                  accept=".pdf,.doc,.docx"
                  className="w-full px-4 py-3 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-transparent dark:bg-gray-700 dark:text-white outline-none transition file:mr-4 file:py-2 file:px-4 file:rounded-lg file:border-0 file:text-sm file:font-semibold file:bg-indigo-50 file:text-indigo-700 hover:file:bg-indigo-100 dark:file:bg-indigo-900 dark:file:text-indigo-300"
                />
                {resume && (
                  <p className="mt-2 text-sm text-gray-600 dark:text-gray-400">
                    Selected: {resume.name}
                  </p>
                )}
              </div>

              <div className="pt-4">
                <button
                  type="submit"
                  disabled={loading}
                  className="w-full bg-indigo-600 hover:bg-indigo-700 disabled:bg-indigo-400 text-white font-semibold py-3 px-6 rounded-lg transition-colors"
                >
                  {loading ? 'Registering Candidate...' : 'Register Candidate'}
                </button>
              </div>
            </form>

            {/* Info Box */}
            <div className="mt-8 p-4 bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-lg">
              <p className="text-sm text-blue-800 dark:text-blue-300">
                <strong>Note:</strong> Upon successful registration, credentials (email and password) will be automatically sent to the candidate's email address.
                The candidate can use these credentials to log in to the platform.
              </p>
            </div>
          </div>
        )}

        {/* Manage Candidates Tab */}
        {activeTab === 'candidates' && (
          <div className="bg-white dark:bg-gray-800 rounded-2xl shadow-xl p-8">
            <div className="mb-8">
              <h2 className="text-3xl font-bold text-gray-900 dark:text-white mb-2">Manage Candidates</h2>
              <p className="text-gray-600 dark:text-gray-300">
                View all registered candidates and manage their login access.
              </p>
            </div>

            {loadingCandidates ? (
              <div className="text-center py-12">
                <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-indigo-600 mx-auto"></div>
                <p className="mt-4 text-gray-600 dark:text-gray-400">Loading candidates...</p>
              </div>
            ) : candidates.length === 0 ? (
              <div className="text-center py-12">
                <p className="text-gray-600 dark:text-gray-400">No candidates registered yet.</p>
              </div>
            ) : (
              <div className="overflow-x-auto">
                <table className="min-w-full divide-y divide-gray-200 dark:divide-gray-700">
                  <thead className="bg-gray-50 dark:bg-gray-700">
                    <tr>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">
                        Email
                      </th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">
                        Username
                      </th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">
                        Status
                      </th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">
                        Registered
                      </th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">
                        Actions
                      </th>
                    </tr>
                  </thead>
                  <tbody className="bg-white dark:bg-gray-800 divide-y divide-gray-200 dark:divide-gray-700">
                    {candidates.map((candidate) => (
                      <tr key={candidate.id} className="hover:bg-gray-50 dark:hover:bg-gray-700">
                        <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900 dark:text-white">
                          {candidate.email}
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500 dark:text-gray-400">
                          {candidate.username}
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap">
                          <span className={`inline-flex px-2 py-1 text-xs font-semibold rounded-full ${candidate.login_disabled
                            ? 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200'
                            : 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200'
                            }`}>
                            {candidate.login_disabled ? 'Login Disabled' : 'Login Enabled'}
                          </span>
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500 dark:text-gray-400">
                          {new Date(candidate.created_at).toLocaleDateString()}
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm">
                          <button
                            onClick={() => toggleCandidateLogin(candidate.id)}
                            className={`px-4 py-2 rounded-lg font-medium transition-colors ${candidate.login_disabled
                              ? 'bg-green-600 hover:bg-green-700 text-white'
                              : 'bg-red-600 hover:bg-red-700 text-white'
                              }`}
                          >
                            {candidate.login_disabled ? 'Enable Login' : 'Disable Login'}
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        )}
      </main>
    </div>
  )
}

