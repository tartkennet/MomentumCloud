'use strict';

// Display the next future cron slot without moving the missed publication
// deadline. The frozen observer's 90-minute monitor rule remains unchanged.
function monitor(data, now=Date.now()) {
  const expected=Date.parse(data.operations.next_expected_attempt_at);
  let next;
  for(let offset=0;offset<9&&!next;offset++) {
    const day=new Date(now);day.setUTCDate(day.getUTCDate()+offset);
    if(![2,3,4,5,6].includes(day.getUTCDay()))continue;
    for(const hour of [0,3,6,9]) {
      const slot=new Date(day);slot.setUTCHours(hour,35,0,0);
      if(slot.getTime()>now){next=slot.toISOString();break;}
    }
  }
  return {delayed:now>expected+data.operations.delay_grace_minutes*60000,
    expected_attempt_at:data.operations.next_expected_attempt_at,
    next_scheduled_attempt_at:next};
}

module.exports={monitor};
