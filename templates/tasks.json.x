{
  "tasks":
  [
#set first = 1
#for $task in $tasks
#if first == 1# #set first = 0# #else#    ,#end if#
    { "id": "$task", "href": "/vdsm-api/tasks/$task" }
#end for
  ]
}
