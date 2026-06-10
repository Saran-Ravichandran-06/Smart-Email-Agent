import { useCallback, useEffect, useMemo } from 'react'

import { ApiError } from '@/api/client'
import {
  fetchEmailById,
  fetchEmailCleaned,
  fetchEmails,
  syncEmails,
} from '@/api/emails'
import { fetchFollowups } from '@/api/followups'
import { fetchTasks } from '@/api/tasks'
import { apiPriorityParam } from '@/lib/priority'
import { useAppStore } from '@/store/useAppStore'
import { useEmailStore } from '@/store/useEmailStore'
import { useFollowupStore } from '@/store/useFollowupStore'
import { useTaskStore } from '@/store/useTaskStore'

let emailsInflight: Promise<void> | null = null

function errorMessage(error: unknown): string {
  if (error instanceof ApiError) {
    return error.message
  }
  if (error instanceof Error) {
    return error.message
  }
  return 'An unexpected error occurred.'
}

export function useInboxEmails() {
  const emails = useEmailStore((s) => s.emails)
  const priorityFilter = useEmailStore((s) => s.priorityFilter)
  const listLoadedPriority = useEmailStore((s) => s.listLoadedPriority)
  const readEmailIds = useEmailStore((s) => s.readEmailIds)
  const listError = useEmailStore((s) => s.listError)
  const setEmails = useEmailStore((s) => s.setEmails)
  const setListLoadedPriority = useEmailStore((s) => s.setListLoadedPriority)
  const setListError = useEmailStore((s) => s.setListError)
  const setLoading = useAppStore((s) => s.setLoading)
  const loading = useAppStore((s) => s.loading.emails)

  const loadEmails = useCallback(async (force = false) => {
    if (!force && listLoadedPriority === priorityFilter) {
      return
    }
    if (emailsInflight) {
      return emailsInflight
    }
    emailsInflight = (async () => {
    setLoading('emails', true)
    setListError(null)
    try {
      const priority = apiPriorityParam(priorityFilter)
      const data = await fetchEmails(priority)
      setEmails(data)
      setListLoadedPriority(priorityFilter)
    } catch (error) {
      setListError(errorMessage(error))
      setEmails([])
    } finally {
      setLoading('emails', false)
      emailsInflight = null
    }
    })()
    return emailsInflight
  }, [listLoadedPriority, priorityFilter, setEmails, setListError, setListLoadedPriority, setLoading])

  const syncInbox = useCallback(async () => {
    setLoading('emails', true)
    setListError(null)
    try {
      await syncEmails()
      await loadEmails(true)
    } catch (error) {
      setListError(errorMessage(error))
    } finally {
      setLoading('emails', false)
    }
  }, [loadEmails, setListError, setLoading])

  useEffect(() => {
    void loadEmails()
  }, [loadEmails])

  const filteredEmails = useMemo(() => {
    if (priorityFilter !== 'unread') {
      return emails
    }
    return emails.filter((email) => !readEmailIds.includes(email.id))
  }, [emails, priorityFilter, readEmailIds])

  return {
    emails: filteredEmails,
    loading,
    listError,
    priorityFilter,
    loadEmails,
    syncInbox,
  }
}

export function useEmailDetail(emailId: number | null) {
  const setLoading = useAppStore((s) => s.setLoading)
  const detailLoading = useAppStore((s) => s.loading.emailDetail)
  const tasksLoading = useAppStore((s) => s.loading.tasks)

  const selectedEmail = useEmailStore((s) => s.selectedEmail)
  const detailLoadedEmailId = useEmailStore((s) => s.detailLoadedEmailId)
  const cleanedBody = useEmailStore((s) => s.cleanedBody)
  const detailError = useEmailStore((s) => s.detailError)
  const setSelectedEmail = useEmailStore((s) => s.setSelectedEmail)
  const setDetailLoadedEmailId = useEmailStore((s) => s.setDetailLoadedEmailId)
  const setCleanedBody = useEmailStore((s) => s.setCleanedBody)
  const setDetailError = useEmailStore((s) => s.setDetailError)
  const markAsRead = useEmailStore((s) => s.markAsRead)
  const resetDetail = useEmailStore((s) => s.resetDetail)

  const tasks = useTaskStore((s) => s.tasks)
  const taskEmailId = useTaskStore((s) => s.taskEmailId)
  const tasksError = useTaskStore((s) => s.tasksError)
  const setTasks = useTaskStore((s) => s.setTasks)
  const setTasksError = useTaskStore((s) => s.setTasksError)

  const followups = useFollowupStore((s) => s.followups)
  const getByThreadId = useFollowupStore((s) => s.getByThreadId)
  const setFollowups = useFollowupStore((s) => s.setFollowups)
  const setFollowupsError = useFollowupStore((s) => s.setFollowupsError)

  const loadDetail = useCallback(
    async (id: number) => {
      if (
        detailLoadedEmailId === id &&
        selectedEmail?.id === id &&
        cleanedBody !== null &&
        taskEmailId === id
      ) {
        markAsRead(id)
        return
      }

      setLoading('emailDetail', true)
      setLoading('tasks', true)
      setDetailError(null)
      setTasksError(null)
      setFollowupsError(null)

      try {
        const email = await fetchEmailById(id)
        setSelectedEmail(email)
        markAsRead(id)

        const [cleaned, emailTasks, allFollowups] = await Promise.all([
          fetchEmailCleaned(id),
          fetchTasks({ emailId: id }),
          fetchFollowups(),
        ])

        setCleanedBody(cleaned?.body_cleaned ?? email.body)
        setTasks(emailTasks, id)
        setFollowups(allFollowups)
        setDetailLoadedEmailId(id)
      } catch (error) {
        setDetailError(errorMessage(error))
        resetDetail()
      } finally {
        setLoading('emailDetail', false)
        setLoading('tasks', false)
      }
    },
    [
      markAsRead,
      resetDetail,
      cleanedBody,
      detailLoadedEmailId,
      setCleanedBody,
      setDetailError,
      setDetailLoadedEmailId,
      setFollowups,
      setFollowupsError,
      setLoading,
      setSelectedEmail,
      setTasks,
      setTasksError,
      selectedEmail,
      taskEmailId,
    ],
  )

  useEffect(() => {
    if (emailId === null) {
      resetDetail()
      setTasks([], null)
      return
    }
    void loadDetail(emailId)
  }, [emailId, loadDetail, resetDetail, setTasks])

  const threadFollowup = selectedEmail
    ? getByThreadId(selectedEmail.thread_id)
    : undefined

  return {
    selectedEmail,
    cleanedBody,
    tasks,
    threadFollowup,
    followups,
    detailLoading,
    tasksLoading,
    detailError,
    tasksError,
    reloadDetail: emailId !== null ? () => loadDetail(emailId) : undefined,
  }
}
