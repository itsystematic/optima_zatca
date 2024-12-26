import { useAppDispatch, useAppSelector } from "@/app/hooks";
import Loading from "@/components/Loading";
import { setIsAdding } from "@/data/addingState";
import { setCurrentPage } from "@/data/currentPage";
import { setStep } from "@/data/currentStep";
import { addCommercial } from "@/data/dataSlice";
import { MainData } from "@/types";
import { Button, ConfigProvider, Table, TableProps } from "antd";
import React, { useEffect, useState } from "react";
import MainPage from "./MainPage";
import Welcome from "./Welcome";

const Home: React.FC = () => {
  const dispatch = useAppDispatch();
  const [data, setData] = useState<MainData[]>();
  const currentPage = useAppSelector((state) => state.pageReducer.currentPage);
  const [loading, setLoading] = useState<boolean>(true);

  useEffect(() => {
    setLoading(true);
    if (isDev) {setData([]); setLoading(false); return};
    frappe.call({
      method: "optima_zatca.zatca.api.get_companies_registered",
      callback: (r: { message: MainData[] }) => {
        if (r.message.length) {
          r.message.forEach((item) => {
            dispatch(
              addCommercial({
                commercial_register_name: item.commercial_register_name || "",
                commercial_register_number:
                  item.commercial_register_number || "",
                short_address: item.short_address || "",
                building_no: item.building_no || "",
                address_line1: item.address_line1 || "",
                address_line2: item.address_line2 || "",
                city: item.city || "",
                district: item.district || "",
                pincode: item.pincode || "",
                otp: item.otp || "",
                more_info: item.more_info || "",
              })
            );
          });
          setData(r.message);
        } else {
          setData([]);
        }
        setLoading(false);
      },
    });
  }, []);

  const columns: TableProps<MainData>["columns"] = [
    {
      title: "Company",
      dataIndex: "company",
      key: "company",
    },
    {
      title: "Company Name in Arabic",
      dataIndex: "company_name_in_arabic",
      key: "company_name_in_arabic",
    },
    {
      title: "Tax ID",
      dataIndex: "tax_id",
      key: "tax_id",
    },
    {
      title: "Commercial Name",
      dataIndex: "commercial_register_name",
      key: "commercial_register_name",
    },
    {
      title: "Commercial Number",
      dataIndex: "commercial_register_number",
      key: "commercial_register_number",
      width: "50px",
    },
    {
      title: "Short Address",
      dataIndex: "short_address",
      key: "short_address",
    },
    {
      title: "Building No",
      dataIndex: "building_no",
      key: "building_no",
      width: "20px",
    },
    {
      title: "Street",
      dataIndex: "address_line1",
      key: "address_line1",
    },
    {
      title: "Secondary No",
      dataIndex: "address_line2",
      key: "address_line2",
    },
    {
      title: "City",
      dataIndex: "city",
      key: "city",
    },
    {
      title: "District",
      dataIndex: "district",
      key: "district",
    },
    {
      title: "Postal Code",
      dataIndex: "pincode",
      key: "pincode",
      width: "20px",
    },
  ];

  return (
    <div className="h-screen w-full">
      {/* Show loading screen */}
      {loading ? (
        <Loading />
      ) : data?.length ? (
        currentPage ? (
          <MainPage />
        ) : (
          <div className="p-5 flex flex-col gap-2">
            <ConfigProvider
              theme={{
                token: {
                  colorPrimary: "#483f61", // Custom primary color
                },
                components: {
                  Input: {
                    controlHeightLG: 48,
                    marginLG: 0,
                  },
                  Button: {
                    controlHeightLG: 48,
                  },
                  Modal: {
                    headerBg: "#f3f3f3",
                    contentBg: "#f3f3f3",
                  },
                  Table: {
                    headerBg: "#483f61",
                    headerColor: "#ffffff",
                  },
                },
              }}
            >
              <Button
                type="primary"
                onClick={() => {
                  dispatch(setCurrentPage(4));
                  dispatch(setIsAdding(true));
                  dispatch(setStep({ currentStep: 1 }));
                }}
                className="bg-[#483f61] disabled:opacity-90 disabled:text-white self-end"
              >
                Add
              </Button>
              <Table dataSource={data} columns={columns} />
            </ConfigProvider>
          </div>
        )
      ) : (
        // Page sliding view
        <Welcome />
      )}
    </div>
  );
};

export default Home;
