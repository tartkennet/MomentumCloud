"""Validation-only chronological stock conversions and ticker generations.

Legal ratios are composed in raw share units. The separate paired-price
installer converts both exit and daily prices to the original adjusted basis.
Symbol generations must be documented; this module does not infer identity.
"""


def combine(chain, successor):
    quantity, cash = 1.0, 0.0
    for step in chain:
        cash += quantity * float(step.get('cash_per_share', 0))
        quantity *= float(step['shares_per_share'])
    return {**chain[0], 'successor_ticker': successor,
            'valuation_ticker': successor, 'shares_per_share': quantity,
            'cash_per_share': cash, 'action_chain': chain,
            'successor_effective_date': chain[-1]['effective_date']}


def identity(actions, ticker, day, entry=None):
    chain, current, held_since = [], ticker, entry
    for _ in range(32):
        action = actions.get(current)
        if not action or str(action['effective_date']) > str(day):
            break
        effective = str(action['effective_date'])
        if held_since is not None and str(held_since) >= effective:
            break
        if not chain and entry is None and action.get('reintroduced_date'):
            if str(day) >= str(action['reintroduced_date']):
                break
        if chain and effective <= str(chain[-1]['effective_date']):
            raise RuntimeError('Non-chronological corporate-action chain')
        chain.append(dict(action))
        current, held_since = str(action['successor_ticker']), effective
    else:
        raise RuntimeError('Corporate-action chain exceeds safety bound')
    if not chain:
        return ticker, 1.0, None
    action = combine(chain, current)
    return current, action['shares_per_share'], action


def install_dated_action_chain(engine):
    original_resolver = engine.resolve_exit_execution

    def dated_identity(ticker, day, entry=None):
        return identity(engine.STOCK_CORPORATE_ACTIONS, ticker, day, entry)

    engine.valuation_identity = dated_identity

    def planned_entry(ticker, day):
        for actions in (engine.CASH_CORPORATE_ACTIONS, engine.STOCK_CORPORATE_ACTIONS):
            action = actions.get(str(ticker).upper().strip())
            if action and str(day) >= str(action['effective_date']):
                if not action.get('reintroduced_date') or str(day) < str(action['reintroduced_date']):
                    return False
        return True

    engine.has_executable_planned_entry = planned_entry

    def resolve(cache, days, ticker, target, entry, latest):
        chain, current, held_since = [], ticker, entry
        for _ in range(32):
            action = engine.STOCK_CORPORATE_ACTIONS.get(current)
            active = action and str(held_since) < str(action['effective_date']) <= str(latest)
            if not active:
                resolved, row, terminal = original_resolver(cache, days, current, target,
                                                            held_since, latest)
                if not row or not chain:
                    return resolved, row, terminal
                aggregate = combine(chain, current)
                if terminal:
                    if terminal.get('reason') != 'CASH_MERGER':
                        raise RuntimeError('Unsupported terminal action after stock chain')
                    amount = aggregate['shares_per_share'] * float(terminal['cash_per_share']) + aggregate['cash_per_share']
                    aggregate.update(reason='CASH_MERGER', execution='cash-settlement',
                                     cash_per_share=amount,
                                     cash_settlement_effective_date=terminal['effective_date'])
                    aggregate.pop('valuation_ticker')
                    return resolved, {'open': amount, 'close': amount}, aggregate
                converted = dict(row)
                for field in ('open', 'high', 'low', 'close'):
                    if converted.get(field) is not None:
                        converted[field] = float(converted[field]) * aggregate['shares_per_share'] + aggregate['cash_per_share']
                return resolved, converted, aggregate
            effective = str(action['effective_date'])
            for day in days:
                if day < target or day < held_since:
                    continue
                if day >= effective or day > latest:
                    break
                row = engine.get_from_map(cache.get(day, {}), current)
                if row:
                    if not chain:
                        return day, row, None
                    aggregate = combine(chain, current)
                    converted = dict(row)
                    for field in ('open', 'high', 'low', 'close'):
                        if converted.get(field) is not None:
                            converted[field] = float(converted[field]) * aggregate['shares_per_share'] + aggregate['cash_per_share']
                    return day, converted, aggregate
            if chain and effective <= str(chain[-1]['effective_date']):
                raise RuntimeError('Non-chronological corporate-action chain')
            chain.append(dict(action))
            current, held_since = str(action['successor_ticker']), effective
            target = max(str(target), effective)
        raise RuntimeError('Corporate-action chain exceeds safety bound')

    engine.resolve_exit_execution = resolve
