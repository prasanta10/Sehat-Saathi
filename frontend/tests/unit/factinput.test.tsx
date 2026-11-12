import '../../src/i18n'

import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { FactInput } from '../../src/components/FactInput'
import { bundle } from '../../src/content/bundle'
import { setLanguage } from '../../src/i18n'

const spec = bundle.facts['cough_duration_days']!

describe('duration answer', () => {
  beforeEach(() => setLanguage('en'))

  it('quick picks are sent in days', async () => {
    const onAnswer = vi.fn()
    render(<FactInput spec={spec} onAnswer={onAnswer} />)
    await userEvent.click(screen.getByTestId('quick-14'))
    expect(screen.getByTestId('answer-submit')).toHaveTextContent('2 weeks')
    await userEvent.click(screen.getByTestId('answer-submit'))
    expect(onAnswer).toHaveBeenCalledWith(14)
  })

  it('weeks and months convert to days, shown before sending', async () => {
    const onAnswer = vi.fn()
    render(<FactInput spec={spec} onAnswer={onAnswer} />)
    await userEvent.type(screen.getByTestId('answer-number'), '3')
    await userEvent.click(screen.getByTestId('unit-weeks'))
    expect(screen.getByTestId('total-days')).toHaveTextContent('= 21 days in all')
    await userEvent.click(screen.getByTestId('unit-months'))
    expect(screen.getByTestId('total-days')).toHaveTextContent('= 90 days in all')
    await userEvent.click(screen.getByTestId('answer-submit'))
    expect(onAnswer).toHaveBeenCalledWith(90)
  })

  it('stepper and "don\'t know" work; nothing is sent without a number', async () => {
    const onAnswer = vi.fn()
    render(<FactInput spec={spec} onAnswer={onAnswer} />)
    expect(screen.getByTestId('answer-submit')).toBeDisabled()
    await userEvent.click(screen.getByRole('button', { name: 'More' }))
    await userEvent.click(screen.getByRole('button', { name: 'More' }))
    await userEvent.click(screen.getByRole('button', { name: 'Less' }))
    await userEvent.click(screen.getByTestId('answer-submit'))
    expect(onAnswer).toHaveBeenLastCalledWith(1)
    await userEvent.click(screen.getByTestId('answer-unknown'))
    expect(onAnswer).toHaveBeenLastCalledWith('unknown')
  })
})
