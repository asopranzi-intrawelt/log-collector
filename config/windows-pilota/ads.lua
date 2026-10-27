local function field(value)
  if value == nil then return "-" end
  local text = tostring(value):gsub("[%c]", " ")
  if text == "" then return "-" end
  return text
end

function ads(tag, ts, record)
  local data = record["EventData"]
  if type(data) ~= "table" then data = {} end
  local event_id = tonumber(record["EventID"])
  local target = field(data["TargetUserName"])
  local target_domain = field(data["TargetDomainName"])
  local subject = field(data["SubjectUserName"])
  local subject_domain = field(data["SubjectDomainName"])
  local user = target
  local user_domain = target_domain
  if event_id == 4648 or event_id == 4672 or event_id == 1102 or
     event_id == 4719 or event_id == 4720 or event_id == 4732 or event_id == 4733 then
    user = subject
    user_domain = subject_domain
  end
  if user == "-" then
    if target ~= "-" then
      user, user_domain = target, target_domain
    else
      user, user_domain = subject, subject_domain
    end
  end
  local message = string.format(
    "user=%q event=%q logon_type=%q system=%q src_ip=%q time=%q record_id=%q user_domain=%q",
    user,
    field(record["EventID"]),
    field(data["LogonType"]),
    field(record["Computer"]),
    field(data["IpAddress"]),
    field(record["TimeCreated"]),
    field(record["EventRecordID"]),
    user_domain
  )
  if target ~= "-" and (target ~= user or target_domain ~= user_domain) then
    message = message .. string.format(" target_user=%q target_domain=%q", target, target_domain)
  end
  record["message"] = message
  return 2, ts, record
end
