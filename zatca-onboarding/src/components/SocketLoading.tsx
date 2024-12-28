import { Flex, Progress, Typography } from "antd";
import { useEffect, useState } from "react";

const SocketLoading = () => {
  const [realtTimeData, setRealTimeData] = useState<any>();
  useEffect(() => {
    if (isDev) return;
    frappe.realtime.on("zatca", (data: any) => {
      console.log(data);
      setRealTimeData(data);
    });
  }, []);
  return (
    <Flex justify="space-between" className="h-full" vertical>
      {realtTimeData ? (
        <>
          <Flex align="center" justify="center" className="h-full">
            <Typography.Title className="font-bold">
              {"Setting up Zatca..."}
            </Typography.Title>
          </Flex>
          <Flex align="flex-start" className="h-full">
            <Progress
              className="text-xl"
              format={() => `${realtTimeData.message} ${realtTimeData.percentage}%`}
              percent={20}
              percentPosition={{ align: "center", type: "outer" }}
            />
          </Flex>
        </>
      ): null}
    </Flex>
  );
};

export default SocketLoading;
