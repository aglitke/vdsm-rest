{
  "resource": "task",
  "id": "$task.UUID",
  "href": "/vdsm-api/tasks/$task.UUID",
  "verb": "$task.info['verb']",
  "message": "$task.info['message']",
  "code": "$task.info['code']",
  "result": "$task.info['result']",
  "state": "$task.info['state']",
#if $task.target is not None
  "link": "$task.target",
#end if
  "actions": {}
}
